import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote, urlsplit

import httpx
from dotenv import dotenv_values
from pydantic import ValidationError
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from schema.api import ActionRequest, ActionResult, ActionView, BoardActionResponse
from schema.dispatch_action import DispatchAction
from schema.assignment_reservation import AssignmentReservation
from schema.shipment import Shipment
from schema.simulation_clock import SimulationClock
from service.activity import add_activity, record_system_event
from service.dashboard import load_detail
from service.database import PROJECT_ROOT
from service.errors import ProductError
from service.expiration import seconds_remaining, simulated_now
from service.ingest import ingest, persist_orders
from service.dispatch_policy import evaluate_dispatch, save_evaluation
from service.reservations import release_resolved_reservations


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
    denial = None
    action_id = None
    try:
        with Session(engine) as session, session.begin():
            if engine.dialect.name != 'sqlite':
                raise ProductError(503, 'Atomic dispatcher reservations require SQLite')
            # Acquire the database write lock before reading schedules. Commit
            # the reservation before HTTP; no database lock spans network I/O.
            session.execute(text('BEGIN IMMEDIATE'))
            shipment = session.scalar(select(Shipment).where(Shipment.external_id == external_id))
            if shipment is None:
                raise ProductError(404, 'Order not found')
            if kind == 'decline' and shipment.board_missing_at is not None:
                raise ProductError(409, 'Order is no longer present on the board')
            if kind == 'decline' and shipment.status != 'open':
                raise ProductError(409, f'Order is {shipment.status}, not open')
            if (kind == 'accept' and shipment.order_type != 'fixed_rate') or (kind == 'bid' and shipment.order_type != 'open_bid'):
                raise ProductError(409, 'Action does not match the order type')
            clock = session.get(SimulationClock, 1)
            if clock is None:
                raise ProductError(503, 'Simulation clock has not been synced yet')
            if kind == 'decline' and seconds_remaining(shipment.expires_at, simulated_now(clock)) == 0:
                raise ProductError(409, 'Order has expired')
            evaluation = None
            if kind in ('accept', 'bid'):
                checked = evaluate_dispatch(session, shipment, getattr(request, 'bid_rate', None))
                evaluation = save_evaluation(session, shipment, checked)
                if not checked.eligible:
                    denial = ProductError(
                        409, 'Dispatch rejected: ' + '; '.join(
                            f'{item.message} ({item.code})' for item in checked.rejection_details
                        ),
                        evaluation=checked.model_dump(mode='json'),
                    )
                    add_activity(session, 'dispatch.rejected', denial.detail,
                                 shipment_id=shipment.shipment_id,
                                 details={'evaluation_id': str(evaluation.evaluation_id)})
            if denial is None:
                action = DispatchAction(
                    shipment_id=shipment.shipment_id, action_type=kind,
                    evaluation_id=evaluation.evaluation_id if evaluation else None,
                    bid_rate=getattr(request, 'bid_rate', None), carrier_note=request.carrier_note,
                    request_status='submitting', requested_at=datetime.now(timezone.utc),
                )
                session.add(action)
                session.flush()
                if evaluation is not None:
                    session.add(AssignmentReservation(
                        action_id=action.action_id, unit_id=evaluation.candidate_unit_id,
                        busy_from=checked.occupied_window.occupied_from, busy_until=checked.occupied_window.occupied_until,
                        created_at=datetime.now(timezone.utc),
                    ))
                    session.flush()
                add_activity(session, 'action.requested', f'{kind} requested',
                             shipment_id=shipment.shipment_id, action_id=action.action_id)
                action_id = action.action_id
        # Raise after commit so rejected policy evaluations remain reviewable.
        if denial is not None:
            raise denial
        return action_id
    except IntegrityError as exc:
        raise ProductError(409, 'An unresolved submission or conflicting unit reservation already exists') from exc
    except OperationalError as exc:
        if engine.dialect.name == 'sqlite' and (getattr(exc.orig, 'sqlite_errorcode', 0) & 255) in (5, 6):
            raise ProductError(503, 'Dispatcher database is busy; retry before submitting') from exc
        raise


def finish_action(engine, action_id, status, message, board_http_status=None):
    with Session(engine) as session, session.begin():
        action = session.get(DispatchAction, action_id)
        # A concurrent board sync may already have established the outcome.
        if action.request_status == 'succeeded' and status != 'succeeded':
            release_resolved_reservations(session)
            return
        action.request_status = status
        action.board_message = message
        action.board_http_status = board_http_status
        action.resolved_at = datetime.now(timezone.utc) if status != 'unknown' else None
        add_activity(session, f'action.{status}', message,
                     shipment_id=action.shipment_id, action_id=action_id,
                     details={'board_http_status': board_http_status})
        release_resolved_reservations(session)


def result(engine, external_id, action_id, sync_pending):
    with Session(engine) as session:
        return ActionResult(
            action=ActionView.model_validate(session.get(DispatchAction, action_id)),
            order=load_detail(session, external_id),
            sync_pending=sync_pending or session.get(AssignmentReservation, action_id) is not None,
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
        feedback = None
        if response.status_code in (400, 404, 409):
            sync_pending = False
            try:
                await ingest(url, engine=engine, tracked_order_ids={external_id})
            except Exception as exc:
                sync_pending = True
                await asyncio.to_thread(record_system_event, engine, 'sync.error', type(exc).__name__)
            refreshed = await asyncio.to_thread(result, engine, external_id, action_id, sync_pending)
            feedback = {
                'code': 'board_rejected', 'source': 'board', 'board_http_status': response.status_code,
                'suggested_action': ('State refresh failed; restore board connectivity and sync before retrying.'
                                     if sync_pending else
                                     'Review the refreshed order, fleet capacity, and evaluation before choosing a new action.'),
                'state_refreshed': not sync_pending,
                'action_result': refreshed.model_dump(mode='json'),
            }
        raise ProductError(response.status_code if 400 <= response.status_code < 500 else 502,
                           message, feedback=feedback)
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
        await ingest(url, engine=engine, tracked_order_ids={external_id})
    except Exception as exc:
        sync_pending = True
        await asyncio.to_thread(record_system_event, engine, 'sync.error', type(exc).__name__)
    return await asyncio.to_thread(result, engine, external_id, action_id, sync_pending)
