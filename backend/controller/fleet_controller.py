from uuid import UUID

from fastapi import APIRouter

from controller.dependencies import Database, Limit, Offset
from schema.api import Page, UnitDetail, UnitView
from schema.fleet_capacity_response import FleetCapacityResponse
from service import dashboard
from service.fleet import capacity_reports

router = APIRouter(prefix='/api/fleet', tags=['Fleet'])


@router.get('/capacity', response_model=list[FleetCapacityResponse])
def fleet_capacity(
    session: Database, discrepancies_only: bool = False,
) -> list[FleetCapacityResponse]:
    return capacity_reports(session, discrepancies_only)


@router.get('/units', response_model=Page[UnitView])
def units(
    session: Database, limit: Limit = 50, offset: Offset = 0,
    terminal: str | None = None, status: str | None = None, include_missing: bool = False,
):
    return dashboard.list_units(session, limit, offset, terminal, status, include_missing)


@router.get('/units/{unit_id}', response_model=UnitDetail)
def unit(unit_id: UUID, session: Database):
    return dashboard.unit_detail(session, unit_id)


legacy_router = APIRouter(prefix='/fleet', tags=['Fleet'])
legacy_router.add_api_route(
    '/capacity', fleet_capacity, methods=['GET'], response_model=list[FleetCapacityResponse],
)
