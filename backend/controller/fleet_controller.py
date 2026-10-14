from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from schema.fleet_capacity_response import FleetCapacityResponse
from service.database import get_session
from service.fleet import capacity_reports

router = APIRouter(prefix='/fleet', tags=['Fleet'])


@router.get('/capacity', response_model=list[FleetCapacityResponse])
def fleet_capacity(
    session: Annotated[Session, Depends(get_session)], discrepancies_only: bool = False,
) -> list[FleetCapacityResponse]:
    return capacity_reports(session, discrepancies_only)
