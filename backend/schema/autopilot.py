from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schema.api import View
from schema.money import PositiveBid


class AutopilotSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enable_fixed_rate: bool = True
    enable_open_bid: bool = True
    max_orders: int = Field(default=10, ge=1, le=10000, strict=True)
    max_duration_seconds: int = Field(default=300, ge=1, le=86400, strict=True)
    max_estimated_loss_usd: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False)
    min_expected_profit_usd: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False)
    min_expected_margin_pct: Decimal = Field(default=Decimal('15'), ge=0, lt=100, allow_inf_nan=False)
    max_deadhead_miles: Decimal = Field(default=Decimal('100'), ge=0, allow_inf_nan=False)
    max_bid_rate: PositiveBid | None = None
    min_action_interval_seconds: float = Field(default=5, ge=1, le=3600, allow_inf_nan=False)
    max_input_age_seconds: int = Field(default=120, ge=1, le=3600, strict=True)
    max_decision_age_seconds: int = Field(default=30, ge=1, le=120, strict=True)
    max_consecutive_errors: int = Field(default=3, ge=1, le=100, strict=True)
    allow_baseline: bool = False

    @model_validator(mode='after')
    def valid_types(self):
        if not self.enable_fixed_rate and not self.enable_open_bid:
            raise ValueError('Enable at least one booking type')
        if self.enable_open_bid and self.max_bid_rate is None:
            raise ValueError('max_bid_rate is required when open bids are enabled')
        return self


class StartAutopilotRequest(AutopilotSettings):
    run_id: UUID = Field(default_factory=uuid4)
    mode: Literal['shadow', 'live'] = 'shadow'


class AutopilotRunView(View):
    run_id: UUID
    status: str
    mode: str
    settings: AutopilotSettings
    started_at_wall: datetime
    deadline_at_wall: datetime
    stopped_at_wall: datetime | None
    stop_reason: str | None
    orders_reserved: int
    estimated_loss_usd: Decimal
    pending_estimated_loss_usd: Decimal
    consecutive_errors: int
    loss_basis: Literal['booking_time_estimates', 'shadow_decision_estimates']
    seconds_remaining: float
    inflight_attempt_ids: list[UUID]
    submissions_enabled: bool


class AutopilotAttemptView(View):
    attempt_id: UUID
    run_id: UUID
    shipment_id: UUID
    external_id: str
    order_type: str
    status: str
    decision: str | None
    action_id: UUID | None
    candidate_unit_id: UUID | None
    bid_rate: Decimal | None
    model_snapshot: dict
    evaluation_snapshot: dict
    reason_codes: list[str]
    message: str | None
    created_at_wall: datetime
    decided_at_wall: datetime | None
    finished_at_wall: datetime | None
