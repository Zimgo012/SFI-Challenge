from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from schema.scheduling import ScheduleConflict


class PickupRoutingPolicy(BaseModel):
    max_pickup_move_miles: Decimal = Field(default=Decimal('100'), ge=0, allow_inf_nan=False)
    distance_method: Literal['haversine_straight_line'] = 'haversine_straight_line'


class PickupUnitRoute(BaseModel):
    unit_id: UUID
    board_unit_id: int
    unit_number: str
    distance_miles: Decimal | None
    within_move_limit: bool
    available_at_pickup: bool
    schedule_passed: bool
    eligible: bool
    conflicting_assignments: list[ScheduleConflict] = Field(default_factory=list)
    rejection_reasons: list[str]


class PickupRouting(BaseModel):
    external_id: str
    pickup_at: datetime | None = None
    delivery_at: datetime | None = None
    pickup_terminal_id: UUID | None = None
    pickup_terminal_code: str | None = None
    terminal_resolution: Literal['origin_code', 'nearest_origin', 'unresolved'] = 'unresolved'
    routing_candidate_unit_id: UUID | None = None
    policy: PickupRoutingPolicy
    routing_passed: bool = False
    schedule_passed: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    units: list[PickupUnitRoute] = Field(default_factory=list)
