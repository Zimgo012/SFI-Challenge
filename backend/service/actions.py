import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote, urlsplit

import httpx
from dotenv import dotenv_values
from pydantic import ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from schema.api import ActionRequest, ActionResult, ActionView, BoardActionResponse
from schema.dispatch_action import DispatchAction
from schema.shipment import Shipment
from schema.simulation_clock import SimulationClock
from service.activity import add_activity, record_system_event
from service.dashboard import load_detail
from service.database import PROJECT_ROOT
from service.errors import ProductError
from service.expiration import seconds_remaining, simulated_now
from service.ingest import ingest, persist_orders


def board_url() -> str:
    config = dotenv_values(PROJECT_ROOT / '.env')
    url = os.environ.get('EXTERNAL_API_URL', config.get('EXTERNAL_API_URL', ''))
    if not url or not url.strip():
        raise ProductError(503, 'Board API is not configured')
    try:
        parsed = urlsplit(url.strip())
        if parsed.port == 0:
            raise ValueError('Invalid port')
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            raise ValueError('Invalid base URL')
    except ValueError as exc:
        raise ProductError(503, 'Board API must have an absolute HTTP(S) base URL') from exc
    return url.strip().rstrip('/') + '/'


def make_board_client(url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=url, timeout=20.0)


def begin_action(engine: Engine, external_id: str, kind: str, request: ActionRequest):
    try:
        with Session(engine) as session, session.begin():
            shipment = session.scalar(select(Shipment).where(Shipment.external_id == external_id))
            if shipment is None:
                raise ProductError(404, 'Order not found')
            if shipment.board_missing_at is not None:
                raise ProductError(409, 'Order is no longer present on the board')
            if shipment.status != 'open':
                raise ProductError(409, f'Order is {shipment.status}, not open')
            if (kind == 'accept' and shipment.order_type != 'fixed_rate') or (kind == 'bid' and shipment.order_type != 'open_bid'):
                raise ProductError(409, 'Action does not match the order type')
            clock = session.get(SimulationClock, 1)
            if clock is None:
                raise ProductError(503, 'Simulation clock has not been synced yet')
            if seconds_remaining(shipment.expires_at, simulated_now(clock)) == 0:
                raise ProductError(409, 'Order has expired')
            action = DispatchAction(
                shipment_id=shipment.shipment_id, action_type=kind,
                bid_rate=getattr(request, 'bid_rate', None), carrier_note=request.carrier_note,
                request_status='submitting', requested_at=datetime.now(timezone.utc),
            )
            session.add(action)
            session.flush()
            add_activity(session, 'action.requested', f'{kind} requested',
                         shipment_id=shipment.shipment_id, action_id=action.action_id)
            return action.action_id
    except IntegrityError as exc:
        raise ProductError(409, 'An unresolved submission already exists for this order') from exc


def finish_action(engine, action_id, status, message, board_http_status=None):
    with Session(engine) as session, session.begin():
        action = session.get(DispatchAction, action_id)
        # A concurrent board sync may already have established the outcome.
        if action.request_status == 'succeeded' and status == 'unknown':
            return
        action.request_status = status
        action.board_message = message
        action.board_http_status = board_http_status
        action.resolved_at = datetime.now(timezone.utc) if status != 'unknown' else None
        add_activity(session, f'action.{status}', message,
                     shipment_id=action.shipment_id, action_id=action_id,
                     details={'board_http_status': board_http_status})


def result(engine, external_id, action_id, sync_pending):
    with Session(engine) as session:
        return ActionResult(
            action=ActionView.model_validate(session.get(DispatchAction, action_id)),
            order=load_detail(session, external_id), sync_pending=sync_pending,
        )


async def execute_action(engine: Engine, external_id: str, kind: str, request: ActionRequest) -> ActionResult:
    url = board_url()
    action_id = await asyncio.to_thread(begin_action, engine, external_id, kind, request)
    try:
        async with make_board_client(url) as client:
            response = await client.post(
                'orders/' + quote(external_id, safe='') + '/' + kind,
                json=request.model_dump(mode='json', exclude_none=True),
            )
    except httpx.HTTPError as exc:
        await asyncio.to_thread(finish_action, engine, action_id, 'unknown',
                                f'Board submission outcome unknown: {type(exc).__name__}')
        raise ProductError(504 if isinstance(exc, httpx.TimeoutException) else 502,
                           'Board submission outcome is unknown; wait for reconciliation before retrying') from exc
    if not response.is_success:
        try:
            message = str(response.json().get('detail', 'Board rejected the action'))[:2000]
        except (ValueError, AttributeError):
            message = 'Board rejected the action'
        request_status = 'failed' if response.status_code < 500 else 'unknown'
        await asyncio.to_thread(finish_action, engine, action_id, request_status, message, response.status_code)
        raise ProductError(response.status_code if 400 <= response.status_code < 500 else 502, message)
    try:
        body = BoardActionResponse.model_validate(response.json(parse_float=Decimal))
        if not body.ok or body.order.external_id != external_id:
            raise ValueError('Invalid board action response')
        expected_statuses = {
            'accept': ('accepted', 'in_transit', 'completed'),
            'decline': ('declined',),
            'bid': ('bid_submitted', 'bid_lost', 'accepted', 'in_transit', 'completed'),
        }
        if body.order.status not in expected_statuses[kind]:
            raise ValueError('Board action response did not establish the expected outcome')
    except (ValueError, ValidationError) as exc:
        await asyncio.to_thread(finish_action, engine, action_id, 'unknown', 'Invalid board action response', response.status_code)
        raise ProductError(502, 'Board action response could not be verified; reconciliation required') from exc
    try:
        await asyncio.to_thread(persist_orders, engine, [body.order])
        await asyncio.to_thread(finish_action, engine, action_id, 'succeeded', body.message, response.status_code)
    except Exception as exc:
        await asyncio.to_thread(finish_action, engine, action_id, 'unknown', 'Board replied successfully but local persistence failed', response.status_code)
        raise ProductError(502, 'Board accepted the request; local reconciliation is required') from exc
    sync_pending = False
    try:
        await ingest(url, engine=engine)
    except Exception as exc:
        sync_pending = True
        await asyncio.to_thread(record_system_event, engine, 'sync.error', type(exc).__name__)
    return await asyncio.to_thread(result, engine, external_id, action_id, sync_pending)
