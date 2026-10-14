from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScheduleConflict(BaseModel):
    assignment_id: UUID
    shipment_id: UUID
    busy_from: datetime
    busy_until: datetime
    assignment_status: str
