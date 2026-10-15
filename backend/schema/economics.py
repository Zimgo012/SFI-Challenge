from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class EconomicsSource(BaseModel):
    method: str = 'unknown'
    inputs: dict[str, str | None] = Field(default_factory=dict)
    formula: str | None = None


class EconomicsSources(BaseModel):
    payout: EconomicsSource = Field(default_factory=EconomicsSource)
    loaded_cost: EconomicsSource = Field(default_factory=EconomicsSource)
    cost_per_mile: EconomicsSource = Field(default_factory=EconomicsSource)
    projected_deadhead_miles: EconomicsSource = Field(default_factory=EconomicsSource)
    projected_deadhead_cost: EconomicsSource = Field(default_factory=EconomicsSource)
    total_cost: EconomicsSource = Field(default_factory=EconomicsSource)
    gross_profit: EconomicsSource = Field(default_factory=EconomicsSource)
    deadhead_travel_hours: EconomicsSource = Field(default_factory=EconomicsSource)
    shipment_duration_hours: EconomicsSource = Field(default_factory=EconomicsSource)
    turnaround_hours: EconomicsSource = Field(default_factory=EconomicsSource)
    occupied_hours: EconomicsSource = Field(default_factory=EconomicsSource)
    profit_per_hour: EconomicsSource = Field(default_factory=EconomicsSource)
    margin_pct: EconomicsSource = Field(default_factory=EconomicsSource)


class MissingEconomicsInput(BaseModel):
    field: str
    code: str
    message: str


class ExpectedEconomics(BaseModel):
    calculation_version: Literal['deterministic_v1'] = 'deterministic_v1'
    currency: Literal['USD'] = 'USD'
    payout: Decimal | None = None
    loaded_cost: Decimal | None = None
    projected_deadhead_miles: Decimal | None = None
    projected_deadhead_cost: Decimal | None = None
    total_cost: Decimal | None = None
    gross_profit: Decimal | None = None
    margin_pct: Decimal | None = None
    deadhead_travel_hours: Decimal | None = None
    shipment_duration_hours: Decimal | None = None
    turnaround_hours: Decimal | None = None
    occupied_hours: Decimal | None = None
    profit_per_hour: Decimal | None = None
    cost_per_mile: Decimal | None = None
    sources: EconomicsSources = Field(default_factory=EconomicsSources)
    missing_inputs: list[MissingEconomicsInput] = Field(default_factory=list)

    # Read-only compatibility fields share canonical values and cannot drift.
    @computed_field
    @property
    def expected_payout(self) -> Decimal | None:
        return self.payout

    @computed_field
    @property
    def deadhead_cost(self) -> Decimal | None:
        return self.projected_deadhead_cost

    @computed_field
    @property
    def expected_total_cost(self) -> Decimal | None:
        return self.total_cost

    @computed_field
    @property
    def expected_margin_usd(self) -> Decimal | None:
        return self.gross_profit

    @computed_field
    @property
    def expected_margin_pct(self) -> Decimal | None:
        return self.margin_pct

    @computed_field
    @property
    def loaded_cost_source(self) -> str:
        return self.sources.loaded_cost.method

    @computed_field
    @property
    def payout_source(self) -> str:
        return self.sources.payout.method

    @computed_field
    @property
    def missing_reasons(self) -> list[str]:
        return list(dict.fromkeys(item.code for item in self.missing_inputs))
