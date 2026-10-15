from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from schema.activity import Activity
from schema.assignment import ACTIVE_ASSIGNMENT_STATUSES, Assignment
from schema.dispatch_action import DispatchAction
from schema.fleet_unit import FleetUnit
from schema.shipment import Shipment
from schema.terminal import Terminal
from service.activity import add_activity
from service.assignment_occupancy import assignment_occupied_bounds
from service.geography import nearest_terminal
from service.reservations import release_resolved_reservations

CONFIRMED_STATUSES = ('accepted', 'in_transit', 'completed')


def reconcile_bookings(session: Session, sim_time: datetime) -> None:
    terminals = session.scalars(select(Terminal).order_by(Terminal.board_terminal_id)).all()
    by_code = {terminal.code.upper(): terminal for terminal in terminals}
    units = {unit.board_unit_id: unit for unit in session.scalars(select(FleetUnit).where(FleetUnit.board_missing_at.is_(None)))}
    shipments = session.scalars(select(Shipment).where(Shipment.board_missing_at.is_(None)).execution_options(populate_existing=True)).all()
    # Release superseded locks first: a new booking may share a unit with a
    # delivery or reassignment reconciled in this same snapshot.
    for shipment in shipments:
        active = session.scalar(select(Assignment).where(
            Assignment.shipment_id == shipment.shipment_id,
            Assignment.assignment_status.in_(ACTIVE_ASSIGNMENT_STATUSES),
        ))
        if active is None:
            continue
        previous_unit = session.get(FleetUnit, active.unit_id)
        reassigned = (
            shipment.status in CONFIRMED_STATUSES
            and shipment.board_assigned_unit_id is not None
            and previous_unit.board_unit_id != shipment.board_assigned_unit_id
        )
        if reassigned or shipment.status in ('declined', 'bid_lost', 'expired'):
            active.assignment_status = 'cancelled'
            active.cancelled_at = sim_time
            add_activity(session, 'assignment.cancelled',
                         'Assignment superseded by board reassignment' if reassigned else 'Board booking no longer active',
                         shipment_id=shipment.shipment_id,
                         details={'assignment_id': str(active.assignment_id)})
        elif shipment.status == 'completed':
            active.assignment_status = 'completed'
            active.completed_at = shipment.delivery_at or sim_time
    session.flush()

    for shipment in shipments:
        if shipment.status in CONFIRMED_STATUSES and shipment.board_assigned_unit_id is not None:
            unit = units.get(shipment.board_assigned_unit_id)
            origin = by_code.get((shipment.assigned_terminal_code or shipment.origin_terminal_code or '').upper())
            destination = by_code.get((shipment.destination_terminal_code or '').upper())
            origin = origin or nearest_terminal(terminals, shipment.origin_latitude, shipment.origin_longitude)
            destination = destination or nearest_terminal(terminals, shipment.destination_latitude, shipment.destination_longitude)
            if unit and origin and destination and shipment.pickup_at and shipment.delivery_at:
                assignment = session.scalar(select(Assignment).where(
                    Assignment.shipment_id == shipment.shipment_id,
                    Assignment.assignment_status.in_(ACTIVE_ASSIGNMENT_STATUSES),
                ))
                if assignment is None and shipment.status == 'completed':
                    assignment = session.scalar(select(Assignment).where(
                        Assignment.shipment_id == shipment.shipment_id,
                        Assignment.unit_id == unit.unit_id,
                        Assignment.assignment_status == 'completed',
                    ).order_by(Assignment.confirmed_at.desc(), Assignment.assignment_id.desc()))
                    # Completed rows are immutable history, including their interval.
                historical_completion = assignment is not None and assignment.assignment_status == 'completed'
                if not historical_completion:
                    try:
                        with session.begin_nested():
                            occupied_from, occupied_until = assignment_occupied_bounds(session, shipment, unit, assignment, sim_time)
                            is_new = assignment is None
                            if is_new:
                                assignment = Assignment(shipment_id=shipment.shipment_id, confirmed_at=sim_time)
                                session.add(assignment)
                            assignment.unit_id = unit.unit_id
                            assignment.origin_terminal_id = origin.terminal_id
                            assignment.destination_terminal_id = destination.terminal_id
                            assignment.occupied_from = occupied_from
                            assignment.occupied_until = occupied_until
                            assignment.busy_from = shipment.pickup_at
                            assignment.busy_until = shipment.delivery_at
                            assignment.assignment_status = 'confirmed' if shipment.status == 'accepted' else shipment.status
                            assignment.completed_at = shipment.delivery_at if shipment.status == 'completed' else None
                            session.flush()
                            if is_new:
                                add_activity(session, 'assignment.confirmed', 'Board booking mirrored locally',
                                             shipment_id=shipment.shipment_id)
                    except IntegrityError:
                        # Keep upstream truth even if its booking cannot satisfy local
                        # scheduling invariants. Surface the conflict for review.
                        details = {
                            'board_unit_id': shipment.board_assigned_unit_id,
                            'busy_from': shipment.pickup_at.isoformat(),
                            'busy_until': shipment.delivery_at.isoformat(),
                        }
                        previous = session.scalar(select(Activity).where(
                            Activity.shipment_id == shipment.shipment_id,
                            Activity.event_type == 'assignment.conflict',
                        ).order_by(Activity.occurred_at_wall.desc()))
                        if previous is None or previous.details != details:
                            add_activity(session, 'assignment.conflict', 'Board assignment violates local interval or lock rules',
                                         shipment_id=shipment.shipment_id, details=details)

        unresolved = session.scalars(select(DispatchAction).where(
            DispatchAction.shipment_id == shipment.shipment_id,
            DispatchAction.request_status.in_(('submitting', 'unknown')),
        )).all()
        for action in unresolved:
            confirmed = (
                (action.action_type == 'accept' and shipment.status in CONFIRMED_STATUSES and shipment.board_assigned_unit_id is not None)
                or (action.action_type == 'decline' and shipment.status == 'declined')
                or (action.action_type == 'bid' and shipment.status in ('bid_submitted', 'bid_lost', *CONFIRMED_STATUSES)
                    and shipment.winning_bid_rate == action.bid_rate)
            )
            if confirmed:
                action.request_status = 'succeeded'
                action.board_message = 'Outcome reconciled from board snapshot'
                action.resolved_at = datetime.now(timezone.utc)
                add_activity(session, 'action.reconciled', action.board_message,
                             shipment_id=shipment.shipment_id, action_id=action.action_id)
    session.flush()
    release_resolved_reservations(session)
