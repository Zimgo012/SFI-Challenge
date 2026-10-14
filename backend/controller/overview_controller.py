from fastapi import APIRouter

from controller.dependencies import Database
from service import dashboard
from schema.api import Overview

router = APIRouter(prefix='/api', tags=['Overview'])


@router.get('/overview', response_model=Overview)
def overview(session: Database):
    return dashboard.overview(session)
