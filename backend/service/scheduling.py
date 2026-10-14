from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.assignment import ACTIVE_ASSIGNMENT_STATUSES, Assignment
from schema.scheduling import ScheduleConflict
from service.expiration import utc

BOOKABLE_UNIT_STATUSES = ('available', 'assigned', 'in_transit')


def schedule_conflicts(session: Session, unit_ids, pickup_at: datetime, delivery_at: datetime):
    """Find every active overlap, including future locks and retained missing orders."""
    conflicts = {unit_id: [] for unit_id in unit_ids}
    if not conflicts:
        return conflicts
    assignments = session.scalars(select(Assignment).where(
        Assignment.unit_id.in_(unit_ids),
        Assignment.assignment_status.in_(ACTIVE_ASSIGNMENT_STATUSES),
        Assignment.busy_from < utc(delivery_at),
        Assignment.busy_until > utc(pickup_at),
    ).order_by(Assignment.busy_from, Assignment.assignment_id)).all()
    for assignment in assignments:
        conflicts[assignment.unit_id].append(ScheduleConflict(
            assignment_id=assignment.assignment_id, shipment_id=assignment.shipment_id,
            busy_from=utc(assignment.busy_from), busy_until=utc(assignment.busy_until),
            assignment_status=assignment.assignment_status,
        ))
    return conflicts


def unit_schedule_rejections(unit, pickup_at: datetime, conflicts: list[ScheduleConflict]) -> list[str]:
    reasons = []
    if unit.status not in BOOKABLE_UNIT_STATUSES:
        reasons.append('unit_status_unavailable')
    if unit.available_at is not None and utc(unit.available_at) > utc(pickup_at):
        reasons.append('unit_available_after_pickup')
    elif unit.status != 'available' and unit.available_at is None:
        reasons.append('unit_availability_unknown')
    if conflicts:
        reasons.append('assignment_window_overlap')
    return reasons
