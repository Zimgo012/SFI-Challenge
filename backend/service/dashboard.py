from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from schema.activity import Activity
from schema.api import (
    ActionView, ActivityView, AssignmentView, BidView, EvaluationView, LoadDetail,
    LoadView, Overview, Page, ProfitSummary, SystemStatus, TerminalDetail,
    TerminalView, UnitDetail, UnitView,
)
from schema.assignment import Assignment
from schema.dispatch_action import DispatchAction
from schema.evaluation import Evaluation
from schema.fleet_unit import FleetUnit
from schema.shipment import Shipment
from schema.simulation_clock import SimulationClock
from schema.terminal import Terminal
from service.assignments import CONFIRMED_STATUSES
from service.errors import ProductError
from service.expiration import expire_due_offers, seconds_remaining, simulated_now, utc
from service.fleet import ACTIVE_ASSIGNMENT_STATUSES, capacity_reports
from service.system_state import connection_state


def clock_time(session: Session):
    clock = session.get(SimulationClock, 1)
    return simulated_now(clock) if clock else None


def page(session, statement, render, limit, offset):
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    rows = session.scalars(statement.limit(limit).offset(offset)).all()
    return Page(items=[render(row) for row in rows], total=total, limit=limit, offset=offset)


def profit(row: Shipment):
    cost = row.estimated_total_cost
    if cost is None and row.estimated_cost is not None and row.estimated_deadhead_cost is not None:
        cost = row.estimated_cost + row.estimated_deadhead_cost
    payout = row.winning_bid_rate if row.order_type == 'open_bid' else row.offered_rate
    if row.board_missing_at is not None or cost is None or payout is None:
        return None, 'unavailable'
    confirmed = row.status in CONFIRMED_STATUSES and row.board_assigned_unit_id is not None
    conditional = row.status in ('open', 'bid_submitted')
    if not confirmed and not conditional:
        return None, 'unavailable'
    return payout - cost, 'confirmed' if confirmed else 'conditional'


def load_view(row: Shipment, sim_time=None) -> LoadView:
    result = LoadView.model_validate(row)
    result.estimated_profit, result.profit_category = profit(row)
    if row.board_missing_at is not None or sim_time is None:
        result.seconds_remaining = None
    else:
        result.seconds_remaining = seconds_remaining(row.expires_at, sim_time) if row.status == 'open' else 0
    return result


def list_loads(session, limit=50, offset=0, order_type=None, status=None, origin_terminal=None, shipments_only=False, include_missing=False):
    expire_due_offers(session)
    session.commit()
    statement = select(Shipment).order_by(Shipment.board_created_at.desc(), Shipment.external_id)
    if not include_missing:
        statement = statement.where(Shipment.board_missing_at.is_(None))
    if order_type:
        statement = statement.where(Shipment.order_type == order_type)
    if status and status != 'all':
        statement = statement.where(Shipment.status == status)
    if origin_terminal:
        statement = statement.where(func.upper(Shipment.origin_terminal_code) == origin_terminal.upper())
    if shipments_only:
        statement = statement.where(Shipment.status.in_(CONFIRMED_STATUSES), Shipment.board_missing_at.is_(None))
    sim_time = clock_time(session)
    return page(session, statement, lambda row: load_view(row, sim_time), limit, offset)


def load_detail(session: Session, external_id: str) -> LoadDetail:
    expire_due_offers(session)
    session.commit()
    row = session.scalar(select(Shipment).where(Shipment.external_id == external_id))
    if row is None:
        raise ProductError(404, 'Order not found')
    assignment = session.scalar(select(Assignment).where(Assignment.shipment_id == row.shipment_id))
    if row.status not in CONFIRMED_STATUSES or row.board_missing_at is not None:
        assignment = None
    if assignment is not None:
        assigned_unit = session.get(FleetUnit, assignment.unit_id)
        if assigned_unit.board_missing_at is not None or assigned_unit.board_unit_id != row.board_assigned_unit_id:
            assignment = None
    evaluation = session.scalar(select(Evaluation).where(Evaluation.shipment_id == row.shipment_id).order_by(Evaluation.evaluated_at_wall.desc()))
    actions = session.scalars(select(DispatchAction).where(DispatchAction.shipment_id == row.shipment_id).order_by(DispatchAction.requested_at.desc())).all()
    return LoadDetail(
        **load_view(row, clock_time(session)).model_dump(),
        actions=[ActionView.model_validate(action) for action in actions],
        actual_assignment=AssignmentView.model_validate(assignment) if assignment else None,
        latest_evaluation=EvaluationView.model_validate(evaluation) if evaluation else None,
    )


def unit_view(session, row):
    view = UnitView.model_validate(row)
    terminal = session.get(Terminal, row.home_terminal_id)
    view.terminal_code = terminal.code if terminal else None
    return view


def list_units(session, limit=50, offset=0, terminal=None, status=None, include_missing=False):
    statement = select(FleetUnit).join(Terminal).order_by(FleetUnit.unit_number)
    if terminal:
        statement = statement.where(func.upper(Terminal.code) == terminal.upper())
    if status:
        statement = statement.where(FleetUnit.status == status)
    if not include_missing:
        statement = statement.where(FleetUnit.board_missing_at.is_(None))
    return page(session, statement, lambda row: unit_view(session, row), limit, offset)


def unit_detail(session, unit_id: UUID):
    unit = session.get(FleetUnit, unit_id)
    if unit is None:
        raise ProductError(404, 'Fleet unit not found')
    assignment = session.scalar(select(Assignment).where(
        Assignment.unit_id == unit_id, Assignment.assignment_status.in_(ACTIVE_ASSIGNMENT_STATUSES),
    ).join(Shipment).where(
        Shipment.board_missing_at.is_(None), Shipment.status.in_(CONFIRMED_STATUSES),
        Shipment.board_assigned_unit_id == unit.board_unit_id,
    ).order_by(Assignment.busy_until.desc())) if unit.board_missing_at is None else None
    return UnitDetail(
        **unit_view(session, unit).model_dump(),
        actual_assignment=AssignmentView.model_validate(assignment) if assignment else None,
    )


def list_terminals(session, limit=50, offset=0):
    capacities = {report.terminal_code: report for report in capacity_reports(session)}
    def render(row):
        result = TerminalView.model_validate(row)
        result.capacity = capacities.get(row.code)
        return result
    return page(session, select(Terminal).order_by(Terminal.code), render, limit, offset)


def terminal_detail(session, code):
    terminal = session.scalar(select(Terminal).where(func.upper(Terminal.code) == code.upper()))
    if terminal is None:
        raise ProductError(404, 'Terminal not found')
    result = TerminalView.model_validate(terminal)
    result.capacity = next((report for report in capacity_reports(session) if report.terminal_code == terminal.code), None)
    units = session.scalars(select(FleetUnit).where(
        FleetUnit.home_terminal_id == terminal.terminal_id, FleetUnit.board_missing_at.is_(None),
    ).order_by(FleetUnit.unit_number)).all()
    return TerminalDetail(**result.model_dump(), roster=[unit_view(session, unit) for unit in units])


def list_bids(session, limit=50, offset=0):
    bid_exists = select(DispatchAction.action_id).where(
        DispatchAction.shipment_id == Shipment.shipment_id, DispatchAction.action_type == 'bid',
    ).exists()
    statement = select(Shipment).where(
        Shipment.order_type == 'open_bid',
        or_(Shipment.winning_bid_rate.is_not(None), Shipment.status.in_(('bid_submitted', 'bid_lost')), bid_exists),
    ).order_by(Shipment.last_synced_at.desc(), Shipment.external_id)
    sim_time = clock_time(session)
    def render(row):
        action = session.scalar(select(DispatchAction).where(
            DispatchAction.shipment_id == row.shipment_id, DispatchAction.action_type == 'bid',
        ).order_by(DispatchAction.requested_at.desc()))
        outcome = 'unknown'
        if row.board_missing_at is None:
            if row.status == 'bid_submitted':
                outcome = 'pending'
            elif row.status == 'bid_lost':
                outcome = 'lost'
            elif row.status in CONFIRMED_STATUSES:
                outcome = 'won'
            elif action and action.request_status == 'failed':
                outcome = 'rejected'
        return BidView(
            action_id=action.action_id if action else None,
            bid_rate=action.bid_rate if action else row.winning_bid_rate,
            request_status=action.request_status if action else None,
            outcome=outcome, decision_at=utc(row.bid_decision_at) if row.bid_decision_at else None,
            order=load_view(row, sim_time),
        )
    return page(session, statement, render, limit, offset)


def list_activity(session, limit=50, offset=0, external_id=None, event_type=None):
    statement = select(Activity).outerjoin(Shipment).order_by(Activity.occurred_at_wall.desc(), Activity.event_id)
    if external_id:
        statement = statement.where(Shipment.external_id == external_id)
    if event_type:
        statement = statement.where(Activity.event_type == event_type)
    def render(row):
        result = ActivityView.model_validate(row)
        shipment = session.get(Shipment, row.shipment_id) if row.shipment_id else None
        result.external_id = shipment.external_id if shipment else None
        return result
    return page(session, statement, render, limit, offset)


def system_status(session):
    clock = session.get(SimulationClock, 1)
    return SystemStatus(
        sim_time_utc=simulated_now(clock) if clock else None,
        simulation_speed=clock.simulation_speed if clock else None,
        connection_status=connection_state.status,
        connection_changed_at=connection_state.changed_at,
        last_sync_at=utc(clock.last_synced_at) if clock else None,
        last_error=connection_state.last_error,
    )


def overview(session):
    loads = list_loads(session, limit=5, status='open')
    bids = list_bids(session, limit=5)
    terminals = list_terminals(session, limit=5)
    fleet = list_units(session, limit=5)
    shipments = list_loads(session, limit=5, shipments_only=True)
    activity = list_activity(session, limit=5)
    summary = ProfitSummary(
        confirmed_estimated_profit=Decimal('0'), conditional_pending_bid_profit=Decimal('0'),
        confirmed_estimated_count=0, pending_estimated_count=0,
        confirmed_unknown_count=0, pending_unknown_count=0,
    )
    for row in session.scalars(select(Shipment).where(Shipment.board_missing_at.is_(None))):
        amount, category = profit(row)
        if row.status in CONFIRMED_STATUSES:
            if category == 'confirmed':
                summary.confirmed_estimated_profit += amount
                summary.confirmed_estimated_count += 1
            else:
                summary.confirmed_unknown_count += 1
        elif row.status == 'bid_submitted':
            if amount is not None:
                summary.conditional_pending_bid_profit += amount
                summary.pending_estimated_count += 1
            else:
                summary.pending_unknown_count += 1
    return Overview(
        counts={
            'open_loads': loads.total, 'bids': bids.total, 'terminals': terminals.total,
            'fleet_units': fleet.total, 'shipments': shipments.total, 'activity': activity.total,
        },
        profit=summary, loads=loads.items, bids=bids.items, terminals=terminals.items,
        fleet=fleet.items, shipments=shipments.items, activity=activity.items,
    )
