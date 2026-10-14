from decimal import Decimal

from schema.unit_projection import ChainingUnit
from service.geography import pickup_distance_miles, valid_coordinates
from service.scheduling import reservation_conflicts, schedule_conflicts
from service.unit_projection import project_units


def chaining_candidates(session, units, shipment, terminal, max_move):
    projections = project_units(session, units, shipment.pickup_at)
    by_id = {unit.unit_id: unit for unit in units}
    conflicts = schedule_conflicts(session, list(by_id), shipment.pickup_at, shipment.delivery_at)
    reservations = reservation_conflicts(session, list(by_id), shipment.pickup_at, shipment.delivery_at)
    items = []
    distances = {}
    for projection in projections:
        item = ChainingUnit(
            projection=projection,
            at_current_pickup_hub=by_id[projection.unit_id].home_terminal_id == terminal.terminal_id,
            rejection_reasons=list(projection.rejection_reasons),
        )
        items.append(item)
        if projection.status != 'available':
            item.rejection_reasons.append('projected_unit_unavailable')
        if projection.terminal_id != terminal.terminal_id:
            item.rejection_reasons.append('projected_pickup_terminal_mismatch')
        if valid_coordinates(projection.latitude, projection.longitude):
            distance = pickup_distance_miles(projection.latitude, projection.longitude,
                                             shipment.origin_latitude, shipment.origin_longitude)
            distances[projection.unit_id] = distance
            item.distance_miles = distance.quantize(Decimal('0.001'))
            if distance > max_move:
                item.rejection_reasons.append('projected_pickup_move_exceeds_limit')
        else:
            item.rejection_reasons.append('projected_location_unknown')
        if conflicts[projection.unit_id]:
            item.rejection_reasons.append('assignment_window_overlap')
        if reservations[projection.unit_id]:
            item.rejection_reasons.append('assignment_window_reserved')
        item.eligible = not item.rejection_reasons
    eligible = [item for item in items if item.eligible]
    candidate = min(eligible, key=lambda item: (
        distances[item.projection.unit_id], by_id[item.projection.unit_id].employee_code,
        by_id[item.projection.unit_id].board_unit_id,
    )) if eligible else None
    return items, candidate.projection.unit_id if candidate else None
