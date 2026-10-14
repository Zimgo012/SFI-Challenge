from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostPreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    unit_id: UUID | None = None
    bid_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6, allow_inf_nan=False)
