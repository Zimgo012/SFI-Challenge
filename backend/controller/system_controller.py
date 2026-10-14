from fastapi import APIRouter

from controller.dependencies import Database
from service import dashboard
from schema.api import SystemStatus
from schema.dispatch_policy import DispatchPolicy
from service.dispatch_policy import dispatch_policy

router = APIRouter(prefix='/api/system', tags=['System'])


@router.get('/status', response_model=SystemStatus)
def system_status(session: Database):
    return dashboard.system_status(session)


@router.get('/policy', response_model=DispatchPolicy)
def current_dispatch_policy():
    return dispatch_policy()
