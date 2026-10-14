from fastapi import APIRouter

from controller.dependencies import Database, Limit, Offset
from service import dashboard
from schema.api import ActivityView, Page

router = APIRouter(prefix='/api', tags=['Activity'])


@router.get('/activity', response_model=Page[ActivityView])
def activity(
    session: Database, limit: Limit = 50, offset: Offset = 0,
    external_id: str | None = None, event_type: str | None = None,
):
    return dashboard.list_activity(session, limit, offset, external_id, event_type)
