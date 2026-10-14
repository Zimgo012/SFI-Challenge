import os
from decimal import Decimal

from dotenv import dotenv_values
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.fleet_capacity import FleetCapacity
from schema.fleet_unit import FleetUnit
from schema.pickup_routing import PickupRouting, PickupRoutingPolicy, PickupUnitRoute
from schema.shipment import Shipment
from schema.terminal import Terminal
from service.database import PROJECT_ROOT
from service.errors import ProductError
from service.expiration import utc
from service.geography import nearest_terminal, pickup_distance_miles, valid_coordinates
from service.scheduling import schedule_conflicts, unit_schedule_rejections


def routing_policy() -> PickupRoutingPolicy:
    config = dotenv_values(PROJECT_ROOT / '.env')
    value = os.environ.get('MAX_PICKUP_MOVE_MILES', config.get('MAX_PICKUP_MOVE_MILES', '100'))
    try:
        return PickupRoutingPolicy(max_pickup_move_miles=value)
    except ValidationError as exc:
        raise ProductError(503, 'MAX_PICKUP_MOVE_MILES must be a finite non-negative number') from exc


def evaluate_pickup_routing(session: Session, shipment: Shipment) -> PickupRouting:
    result = PickupRouting(
        external_id=shipment.external_id, policy=routing_policy(),
        pickup_at=utc(shipment.pickup_at) if shipment.pickup_at else None,
        delivery_at=utc(shipment.delivery_at) if shipment.delivery_at else None,
    )
    if shipment.board_missing_at is not None:
        result.rejection_reasons.append('order_missing_from_board')
        return result
    terminals = session.scalars(select(Terminal).join(FleetCapacity).where(
        FleetCapacity.board_total_units.is_not(None),
    ).order_by(Terminal.board_terminal_id)).all()
    if shipment.origin_terminal_code:
        terminal = next((row for row in terminals if row.code.upper() == shipment.origin_terminal_code.upper()), None)
        if terminal is None:
            result.rejection_reasons.append('unknown_origin_terminal_code')
            return result
        result.terminal_resolution = 'origin_code'
    else:
        if not valid_coordinates(shipment.origin_latitude, shipment.origin_longitude):
            result.rejection_reasons.append('pickup_coordinates_unknown_or_invalid')
            return result
        terminal = nearest_terminal(terminals, shipment.origin_latitude, shipment.origin_longitude)
        if terminal is None:
            result.rejection_reasons.append('pickup_terminal_unresolved')
            return result
        result.terminal_resolution = 'nearest_origin'
    result.pickup_terminal_id = terminal.terminal_id
    result.pickup_terminal_code = terminal.code
    if not valid_coordinates(shipment.origin_latitude, shipment.origin_longitude):
        result.rejection_reasons.append('pickup_coordinates_unknown_or_invalid')
        return result
    if shipment.pickup_at is None:
        result.rejection_reasons.append('pickup_time_unknown')
        return result
    if shipment.delivery_at is None:
        result.rejection_reasons.append('delivery_time_unknown')
        return result
    if utc(shipment.delivery_at) <= utc(shipment.pickup_at):
        result.rejection_reasons.append('invalid_pickup_delivery_window')
        return result
    units = session.scalars(select(FleetUnit).where(
        FleetUnit.home_terminal_id == terminal.terminal_id,
        FleetUnit.board_missing_at.is_(None),
    ).order_by(FleetUnit.employee_code, FleetUnit.board_unit_id)).all()
    conflicts = schedule_conflicts(
        session, [unit.unit_id for unit in units], shipment.pickup_at, shipment.delivery_at,
    )
    raw_distances = {}
    for unit in units:
        available = unit.status not in ('maintenance', 'off_duty') and (
            unit.status == 'available'
            or (unit.available_at is not None and utc(unit.available_at) <= utc(shipment.pickup_at))
        )
        reasons = []
        if not available:
            reasons.append('unit_unavailable_at_pickup')
        schedule_reasons = unit_schedule_rejections(unit, shipment.pickup_at, conflicts[unit.unit_id])
        reasons.extend(schedule_reasons)
        distance = None
        within_limit = False
        if valid_coordinates(unit.current_latitude, unit.current_longitude):
            distance = pickup_distance_miles(
                unit.current_latitude, unit.current_longitude,
                shipment.origin_latitude, shipment.origin_longitude,
            )
            within_limit = distance <= result.policy.max_pickup_move_miles
            raw_distances[unit.unit_id] = distance
            if not within_limit:
                reasons.append('pickup_move_exceeds_limit')
        else:
            reasons.append('unit_coordinates_unknown_or_invalid')
        result.units.append(PickupUnitRoute(
            unit_id=unit.unit_id, board_unit_id=unit.board_unit_id,
            unit_number=unit.unit_number,
            distance_miles=distance.quantize(Decimal('0.001')) if distance is not None else None,
            within_move_limit=within_limit, available_at_pickup=bool(available),
            schedule_passed=not schedule_reasons,
            eligible=bool(available) and within_limit and not schedule_reasons,
            conflicting_assignments=conflicts[unit.unit_id],
            rejection_reasons=reasons,
        ))
    available_units = [unit for unit in result.units if unit.available_at_pickup]
    if not available_units:
        result.rejection_reasons.append('no_available_units_at_pickup_terminal')
    elif any(unit.distance_miles is None for unit in available_units):
        # The board chooses the unit; unknown positions prevent verification.
        result.rejection_reasons.append('available_unit_coordinates_unknown_or_invalid')
    else:
        # Match the board's one-decimal distance comparison and employee-order
        # tie-break; apply our maximum to unrounded miles, including ties.
        candidate = min(available_units, key=lambda unit: round(float(raw_distances[unit.unit_id]), 1))
        result.routing_candidate_unit_id = candidate.unit_id
        result.schedule_passed = candidate.schedule_passed
        if not candidate.schedule_passed:
            result.rejection_reasons.extend(reason for reason in candidate.rejection_reasons if reason in (
                'unit_status_unavailable', 'unit_available_after_pickup',
                'unit_availability_unknown', 'assignment_window_overlap',
            ))
        if not candidate.within_move_limit:
            result.rejection_reasons.append('pickup_move_exceeds_limit')
    result.routing_passed = not result.rejection_reasons
    return result


def pickup_routing(session: Session, external_id: str) -> PickupRouting:
    shipment = session.scalar(select(Shipment).where(Shipment.external_id == external_id))
    if shipment is None:
        raise ProductError(404, 'Order not found')
    return evaluate_pickup_routing(session, shipment)
