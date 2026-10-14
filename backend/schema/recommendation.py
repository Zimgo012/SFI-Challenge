from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from schema.economics import ExpectedEconomics


class RankingPolicy(BaseModel):
    empty_miles_weight: Decimal = Field(default=Decimal('0.60'), ge=0, le=1, allow_inf_nan=False)
    continuity_weight: Decimal = Field(default=Decimal('0.25'), ge=0, le=1, allow_inf_nan=False)
    utilization_weight: Decimal = Field(default=Decimal('0.15'), ge=0, le=1, allow_inf_nan=False)
    utilization_horizon_hours: Decimal = Field(default=Decimal('24'), ge=1, le=168, allow_inf_nan=False)

    @model_validator(mode='after')
    def positive_weight_sum(self):
        if self.empty_miles_weight + self.continuity_weight + self.utilization_weight <= 0:
            raise ValueError('At least one ranking weight must be positive')
        return self


class RankedMatch(BaseModel):
    rank: int = 0
    external_id: str
    shipment_id: UUID
    unit_id: UUID
    board_unit_id: int
    unit_number: str
    pickup_at: datetime
    delivery_at: datetime
    pickup_terminal_code: str
    projected_latitude: Decimal
    projected_longitude: Decimal
    position_source: str
    source_assignment_id: UUID | None
    deadhead_miles: Decimal
    cost_per_mile: Decimal | None
    deadhead_cost: Decimal | None
    cost_missing_reason: str | None = None
    economics: ExpectedEconomics
    empty_miles_score: Decimal
    continues_previous_route: bool
    previous_assignment_id: UUID | None
    idle_gap_seconds: Decimal | None
    continuity_score: Decimal
    booked_hours: Decimal
    added_loaded_hours: Decimal
    utilization_before: Decimal
    utilization_after: Decimal
    score: Decimal
    booking_ready: bool


class RejectedUnit(BaseModel):
    unit_id: UUID
    rejection_reasons: list[str]


class OrderRecommendations(BaseModel):
    external_id: str
    evaluated_at_sim: datetime
    horizon_end: datetime
    policy: RankingPolicy
    entered_bid_rate: Decimal | None = None
    selected: RankedMatch | None = None
    ranked_units: list[RankedMatch] = Field(default_factory=list)
    rejected_units: list[RejectedUnit] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)


class RecommendationsPage(BaseModel):
    items: list[RankedMatch]
    total: int
    limit: int
    offset: int
    evaluated_at_sim: datetime
    horizon_end: datetime
    policy: RankingPolicy
