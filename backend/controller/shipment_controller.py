from fastapi import APIRouter

from controller.dependencies import Database, Limit, Offset
from service import dashboard
from schema.api import LoadView, Page

router = APIRouter(prefix='/api', tags=['Shipments'])


@router.get('/shipments', response_model=Page[LoadView])
def shipments(session: Database, limit: Limit = 50, offset: Offset = 0):
    return dashboard.list_loads(session, limit, offset, shipments_only=True)
