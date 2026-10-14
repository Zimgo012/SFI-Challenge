from typing import Literal

from fastapi import APIRouter, WebSocket

from controller.dependencies import Database, Limit, Offset
from schema.api import ActionRequest, ActionResult, BidRequest, LoadDetail, LoadView, Page
from schema.load_stream import StreamOrderStatus, StreamOrderType
from service import dashboard
from service.actions import execute_action
from service.load_stream import stream_loads

router = APIRouter(prefix='/api/loads', tags=['Loads'])
OrderType = Literal['fixed_rate', 'open_bid']
OrderStatus = Literal['open', 'accepted', 'declined', 'bid_submitted', 'bid_lost', 'in_transit', 'completed', 'expired', 'all']


@router.get('', response_model=Page[LoadView])
def loads(
    session: Database, limit: Limit = 50, offset: Offset = 0,
    order_type: OrderType | None = None, status: OrderStatus = 'open',
    origin_terminal: str | None = None, include_missing: bool = False,
):
    return dashboard.list_loads(session, limit, offset, order_type, status, origin_terminal, include_missing=include_missing)


@router.websocket('/ws')
async def subscribe_loads(
    websocket: WebSocket, session: Database,
    order_type: StreamOrderType = 'open_bid', status: StreamOrderStatus = 'open',
    origin_terminal: str | None = None,
):
    await stream_loads(
        websocket, session.get_bind(), order_type=order_type,
        status=status, origin_terminal=origin_terminal,
    )


@router.get('/{external_id}', response_model=LoadDetail)
def load_detail(external_id: str, session: Database):
    return dashboard.load_detail(session, external_id)


@router.post('/{external_id}/accept', response_model=ActionResult)
async def accept(external_id: str, session: Database, body: ActionRequest | None = None):
    return await execute_action(session.get_bind(), external_id, 'accept', body or ActionRequest())


@router.post('/{external_id}/decline', response_model=ActionResult)
async def decline(external_id: str, session: Database, body: ActionRequest | None = None):
    return await execute_action(session.get_bind(), external_id, 'decline', body or ActionRequest())


@router.post('/{external_id}/bid', response_model=ActionResult)
async def bid(external_id: str, session: Database, body: BidRequest):
    return await execute_action(session.get_bind(), external_id, 'bid', body)
