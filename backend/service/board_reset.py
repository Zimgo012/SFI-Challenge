from uuid import uuid4

from sqlalchemy import select

from schema.assignment import ACTIVE_ASSIGNMENT_STATUSES, Assignment
from schema.assignment_reservation import AssignmentReservation
from schema.dispatch_action import DispatchAction
from schema.shipment import Shipment
from schema.simulation_clock import SimulationClock
from service.activity import add_activity
from service.expiration import utc


def retire_reset_state(session, clock, orders, missing_ids, wall_now):
    """Require authoritative 404s plus clock/counter reset evidence, never absence alone."""
    known = list(session.scalars(select(Shipment).where(Shipment.board_retired_at.is_(None))))
    known_ids = {row.external_id for row in known}
    if not known_ids or not known_ids.issubset(missing_ids or set()):
        return False
    previous = session.get(SimulationClock, 1)
    if previous and utc(clock.wall_time_utc) <= utc(previous.wall_time_utc):
        return False
    old_counter = max((row.board_order_id or 0 for row in known), default=0)
    counter_reset = any(order.external_id not in known_ids and order.id <= old_counter for order in orders)
    clock_reset = previous is not None and (utc(previous.sim_time_utc) - utc(clock.sim_time_utc)).total_seconds() > 1
    if not counter_reset and not clock_reset:
        return False
    shipment_ids = [row.shipment_id for row in known]
    for row in known:
        row.board_retired_at = wall_now
        row.board_missing_at = row.board_missing_at or wall_now
    for assignment in session.scalars(select(Assignment).where(Assignment.shipment_id.in_(shipment_ids))):
        assignment.lock_retired_at = wall_now
        if assignment.assignment_status in ACTIVE_ASSIGNMENT_STATUSES:
            assignment.assignment_status = 'cancelled'
            assignment.cancelled_at = clock.sim_time_utc
        add_activity(session, 'assignment.reset_retired', 'Previous board generation lock retired; history retained',
            shipment_id=assignment.shipment_id, details={'assignment_id': str(assignment.assignment_id)})
    actions = list(session.scalars(select(DispatchAction).where(DispatchAction.shipment_id.in_(shipment_ids))))
    for action in actions:
        if action.request_status in ('submitting', 'unknown'):
            action.request_status = 'failed'
            action.board_message = 'Previous board generation was reset; submission retired locally'
            action.resolved_at = wall_now
        hold = session.get(AssignmentReservation, action.action_id)
        if hold is not None:
            session.delete(hold)
            add_activity(session, 'reservation.reset_retired', 'Previous board generation reservation released',
                         shipment_id=action.shipment_id, action_id=action.action_id)
    add_activity(session, 'board.reset_detected', 'Confirmed board reset; old identities and locks retired',
        details={'generation_id': str(uuid4()), 'retired_order_count': len(known),
                 'counter_reset': counter_reset, 'clock_rewind': clock_reset})
    session.flush()
    return True
