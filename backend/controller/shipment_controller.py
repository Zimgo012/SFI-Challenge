from fastapi import APIRouter

from controller.dependencies import CleanupCount, Database, Limit, Offset
from service import dashboard
from schema.api import LoadView, Page
from schema.history_cleanup import HistoryCleanupResult
from service.history_cleanup import cleanup_history

router = APIRouter(prefix='/api', tags=['Shipments'])


@router.get('/shipments', response_model=Page[LoadView])
def shipments(session: Database, limit: Limit = 50, offset: Offset = 0):
    return dashboard.list_loads(session, limit, offset, shipments_only=True)


@router.delete('/shipments/oldest', response_model=HistoryCleanupResult)
def delete_oldest_shipments(session: Database, count: CleanupCount, dry_run: bool = False):
    return cleanup_history(session, 'shipments', count, dry_run)
