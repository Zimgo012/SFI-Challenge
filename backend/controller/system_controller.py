from fastapi import APIRouter

from controller.dependencies import Database
from service import dashboard
from schema.api import SystemStatus

router = APIRouter(prefix='/api/system', tags=['System'])


@router.get('/status', response_model=SystemStatus)
def system_status(session: Database):
    return dashboard.system_status(session)
