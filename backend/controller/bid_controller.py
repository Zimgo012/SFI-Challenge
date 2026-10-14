from fastapi import APIRouter

from controller.dependencies import Database, Limit, Offset
from service import dashboard
from schema.api import BidView, Page

router = APIRouter(prefix='/api', tags=['Bids'])


@router.get('/bids', response_model=Page[BidView])
def bids(session: Database, limit: Limit = 50, offset: Offset = 0):
    return dashboard.list_bids(session, limit, offset)
