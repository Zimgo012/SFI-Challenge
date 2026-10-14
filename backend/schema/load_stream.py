from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from schema.api import LoadView, SystemStatus

StreamOrderType = Literal['fixed_rate', 'open_bid', 'all']
StreamOrderStatus = Literal[
    'open', 'accepted', 'declined', 'bid_submitted', 'bid_lost',
    'in_transit', 'completed', 'expired', 'all',
]


class LoadStreamState(BaseModel):
    items: list[LoadView]
    system: SystemStatus


class LoadStreamMessage(LoadStreamState):
    event: Literal['loads.snapshot', 'loads.updated', 'loads.heartbeat']
    revision: int
    sent_at: datetime
