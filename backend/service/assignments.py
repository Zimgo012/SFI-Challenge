import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.assignment import Assignment
from schema.dispatch_action import DispatchAction
from schema.fleet_unit import FleetUnit
from schema.shipment import Shipment
from schema.terminal import Terminal
from service.activity import add_activity

CONFIRMED_STATUSES = ('accepted', 'in_transit', 'completed')


def nearest_terminal(terminals: list[Terminal], latitude, longitude):
    if latitude is None or longitude is None:
        return None
    def distance(terminal):
        lat1, lat2 = math.radians(float(latitude)), math.radians(float(terminal.latitude))
        delta_lat = lat2 - lat1
        delta_lon = math.radians(float(terminal.longitude) - float(longitude))
        return math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    candidates = [terminal for terminal in terminals if terminal.latitude is not None and terminal.longitude is not None]
    return min(candidates, key=distance) if candidates else None


def reconcile_bookings(session: Session, sim_time: datetime) -> None:
    terminals = session.scalars(select(Terminal).order_by(Terminal.board_terminal_id)).all()
    by_code = {terminal.code.upper(): terminal for terminal in terminals}
    units = {unit.board_unit_id: unit for unit in session.scalars(select(FleetUnit).where(FleetUnit.board_missing_at.is_(None)))}
    shipments = session.scalars(select(Shipment).where(Shipment.board_missing_at.is_(None)).execution_options(populate_existing=True)).all()
    for shipment in shipments:
        if shipment.status in CONFIRMED_STATUSES and shipment.board_assigned_unit_id is not None:
            unit = units.get(shipment.board_assigned_unit_id)
            origin = by_code.get((shipment.assigned_terminal_code or shipment.origin_terminal_code or '').upper())
            destination = by_code.get((shipment.destination_terminal_code or '').upper())
            origin = origin or nearest_terminal(terminals, shipment.origin_latitude, shipment.origin_longitude)
            destination = destination or nearest_terminal(terminals, shipment.destination_latitude, shipment.destination_longitude)
            if unit and origin and destination and shipment.pickup_at and shipment.delivery_at:
                assignment = session.scalar(select(Assignment).where(Assignment.shipment_id == shipment.shipment_id))
                if assignment is None:
                    assignment = Assignment(shipment_id=shipment.shipment_id, confirmed_at=sim_time)
                    session.add(assignment)
                    is_new = True
                else:
                    is_new = False
                assignment.unit_id = unit.unit_id
                assignment.origin_terminal_id = origin.terminal_id
                assignment.destination_terminal_id = destination.terminal_id
                assignment.busy_from = shipment.pickup_at
                assignment.busy_until = shipment.delivery_at
                assignment.assignment_status = 'confirmed' if shipment.status == 'accepted' else shipment.status
                assignment.completed_at = (shipment.delivery_at or sim_time) if shipment.status == 'completed' else None
                if is_new:
                    add_activity(session, 'assignment.confirmed', 'Board booking mirrored locally', shipment_id=shipment.shipment_id)

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
