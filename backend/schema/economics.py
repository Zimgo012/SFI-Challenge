from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ExpectedEconomics(BaseModel):
    loaded_cost: Decimal | None = None
    loaded_cost_source: Literal['board_loaded_cost', 'distance_times_cost_per_mile', 'unknown'] = 'unknown'
    cost_per_mile: Decimal | None = None
    deadhead_cost: Decimal | None = None
    expected_total_cost: Decimal | None = None
    expected_payout: Decimal | None = None
    payout_source: Literal['fixed_rate_offer', 'entered_bid', 'unknown'] = 'unknown'
    expected_margin_usd: Decimal | None = None
    expected_margin_pct: Decimal | None = None
    missing_reasons: list[str] = Field(default_factory=list)
