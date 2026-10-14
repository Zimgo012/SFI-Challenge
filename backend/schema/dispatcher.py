"""Import all dispatcher models so Alembic sees the complete metadata."""

from schema.base import Base
from schema.terminal import Terminal
from schema.fleet_unit import FleetUnit
from schema.shipment import Shipment
from schema.evaluation import Evaluation
from schema.dispatch_action import DispatchAction
from schema.assignment import Assignment
from schema.historical_shipment import HistoricalShipment
from schema.simulation_clock import SimulationClock

__all__ = [
    'Base',
    'Terminal',
    'FleetUnit',
    'Shipment',
    'Evaluation',
    'DispatchAction',
    'Assignment',
    'HistoricalShipment',
    'SimulationClock',
]
