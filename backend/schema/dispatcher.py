"""Import all dispatcher models so Alembic sees the complete metadata."""

from schema.base import Base
from schema.terminal import Terminal
from schema.fleet_unit import FleetUnit
from schema.shipment import Shipment
from schema.evaluation import Evaluation
from schema.dispatch_action import DispatchAction
from schema.assignment import Assignment
from schema.assignment_reservation import AssignmentReservation
from schema.historical_shipment import HistoricalShipment
from schema.simulation_clock import SimulationClock
from schema.fleet_capacity import FleetCapacity
from schema.activity import Activity
from schema.autopilot_run import AutopilotRun
from schema.allocation_plan import AllocationPlan, AllocationReservation
from schema.autopilot_attempt import AutopilotAttempt
from schema.observed_cohort import ObservedCohort, ObservedComparison
from schema.live_audit import LiveBatchAudit, LiveSubmissionAudit
from schema.prediction_observation import PredictionObservation

__all__ = [
    'Base',
    'Terminal',
    'FleetUnit',
    'Shipment',
    'Evaluation',
    'DispatchAction',
    'Assignment',
    'AssignmentReservation',
    'HistoricalShipment',
    'SimulationClock',
    'FleetCapacity',
    'Activity',
    'AutopilotRun',
    'AutopilotAttempt',
    'AllocationPlan',
    'AllocationReservation',
    'ObservedCohort',
    'ObservedComparison',
    'LiveBatchAudit',
    'LiveSubmissionAudit',
    'PredictionObservation',
]
