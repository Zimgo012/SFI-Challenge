from typing import Literal
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket

from controller.dependencies import Database, Limit, Offset
from schema.api import ActionRequest, ActionResult, BidRequest, LoadDetail, LoadView, Page
from schema.load_stream import StreamOrderStatus, StreamOrderType
from schema.pickup_routing import PickupRouting
from schema.recommendation import OrderRecommendations, RecommendationsPage
from schema.cost_preview import CostPreviewRequest
from schema.dispatch_policy import DispatchEvaluation
from service.dispatch_policy import dispatch_evaluation
from service import dashboard
from service.actions import execute_action
from service.load_stream import stream_loads
from service.pickup_routing import pickup_routing
from service.ranking import order_recommendations, recommendations

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


@router.get('/recommendations', response_model=RecommendationsPage)
def ranked_recommendations(
    session: Database, limit: Limit = 50, offset: Offset = 0,
    unit_id: UUID | None = None, order_type: OrderType | None = None,
    origin_terminal: str | None = None, bookable_only: bool = False,
):
    return recommendations(session, limit, offset, unit_id, order_type, origin_terminal, bookable_only)


@router.get('/{external_id}/recommendations', response_model=OrderRecommendations)
def ranked_units(
    external_id: str, session: Database, unit_id: UUID | None = None,
    bid_rate: Decimal | None = Query(default=None, gt=0, max_digits=18, decimal_places=6, allow_inf_nan=False),
):
    return order_recommendations(session, external_id, unit_id, bid_rate)


@router.post('/{external_id}/cost-preview', response_model=OrderRecommendations)
def cost_preview(external_id: str, body: CostPreviewRequest, session: Database):
    return order_recommendations(session, external_id, body.unit_id, body.bid_rate)


@router.post('/{external_id}/evaluate', response_model=DispatchEvaluation)
def evaluate(external_id: str, body: CostPreviewRequest, session: Database):
    return dispatch_evaluation(session, external_id, body.bid_rate, body.unit_id)


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


@router.get('/{external_id}/routing', response_model=PickupRouting)
def load_pickup_routing(external_id: str, session: Database):
    return pickup_routing(session, external_id)


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
