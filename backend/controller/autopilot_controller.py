from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from controller.dependencies import Limit, Offset
from schema.api import Page
from schema.autopilot import AutopilotAttemptView, AutopilotRunView, StartAutopilotRequest
from service import autopilot
from service.database import get_engine

router = APIRouter(prefix='/api/autopilot', tags=['Autopilot'])
DatabaseEngine = Annotated[Engine, Depends(get_engine)]


@router.post('/runs', response_model=AutopilotRunView)
def start_run(body: StartAutopilotRequest, engine: DatabaseEngine):
    return autopilot.start_run(engine, body)


@router.get('/runs', response_model=Page[AutopilotRunView])
def runs(engine: DatabaseEngine, limit: Limit = 50, offset: Offset = 0):
    return autopilot.list_runs(engine, limit, offset)


@router.get('/runs/{run_id}', response_model=AutopilotRunView)
def run(run_id: UUID, engine: DatabaseEngine):
    return autopilot.get_run(engine, run_id)


@router.post('/runs/{run_id}/stop', response_model=AutopilotRunView)
def stop_run(run_id: UUID, engine: DatabaseEngine):
    return autopilot.get_run(engine, run_id, stop=True)


@router.get('/runs/{run_id}/attempts', response_model=Page[AutopilotAttemptView])
def attempts(run_id: UUID, engine: DatabaseEngine, limit: Limit = 50, offset: Offset = 0):
    return autopilot.list_attempts(engine, run_id, limit, offset)
