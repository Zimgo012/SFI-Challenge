from datetime import datetime, timezone
from decimal import Decimal
import os

from dotenv import dotenv_values
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from schema.autopilot import AutopilotSettings
from schema.autopilot_attempt import AutopilotAttempt
from schema.autopilot_run import AutopilotRun
from schema.dispatch_action import DispatchAction
from schema.evaluation import Evaluation
from schema.fleet_unit import FleetUnit
from schema.shipment import Shipment
from schema.simulation_clock import SimulationClock
from service.activity import add_activity
from service.database import PROJECT_ROOT
from service.errors import ProductError
from service.expiration import utc
from service.reservations import release_resolved_reservations

INFLIGHT = ('evaluating', 'ready', 'submitting')


def wall_now():
    return datetime.now(timezone.utc)


def live_enabled():
    values = dotenv_values(PROJECT_ROOT / '.env')
    return os.environ.get('AUTOPILOT_LIVE_ENABLED', values.get('AUTOPILOT_LIVE_ENABLED', 'false')).lower() == 'true'


def stop_run_record(session, run, reason):
    if run.status == 'running':
        run.status, run.stop_reason, run.stopped_at_wall = 'stopped', reason, wall_now()
        add_activity(session, 'autopilot.stopped', f'Autopilot stopped: {reason}',
                     details={'run_id': str(run.run_id), 'reason': reason})


def refresh_loss(session, run):
    loss, pending = Decimal('0'), Decimal('0')
    attempts = session.scalars(select(AutopilotAttempt).where(AutopilotAttempt.run_id == run.run_id)).all()
    for attempt in attempts:
        if run.mode == 'shadow':
            if attempt.status == 'shadow':
                profit = attempt.evaluation_snapshot.get('economics', {}).get('gross_profit')
                if profit is not None:
                    loss += max(-Decimal(str(profit)), 0)
            continue
        action = session.get(DispatchAction, attempt.action_id) if attempt.action_id else None
        if action is None or action.request_status == 'failed':
            continue
        quote = session.get(Evaluation, action.evaluation_id) if action.evaluation_id else None
        if quote is None or quote.profit_usd is None:
            if action.request_status == 'succeeded':
                stop_run_record(session, run, 'booking_economics_missing')
            continue
        shipment = session.get(Shipment, action.shipment_id)
        amount = max(-quote.profit_usd, 0)
        if action.request_status == 'succeeded' and shipment.status in ('accepted', 'in_transit', 'completed'):
            loss += amount
        elif action.request_status in ('submitting', 'unknown') or shipment.status == 'bid_submitted':
            pending += amount
    run.estimated_loss_usd, run.pending_estimated_loss_usd = loss, pending


def check_run_limits(session, run):
    refresh_loss(session, run)
    if run.status != 'running':
        return run.stop_reason
    config = AutopilotSettings.model_validate(run.settings)
    inflight = session.scalar(select(AutopilotAttempt.attempt_id).where(
        AutopilotAttempt.run_id == run.run_id, AutopilotAttempt.status.in_(INFLIGHT),
    )) is not None
    reason = None
    if wall_now() >= utc(run.deadline_at_wall):
        reason = 'time_limit_reached'
    elif run.mode == 'live' and not live_enabled():
        reason = 'live_disabled'
    elif run.orders_reserved >= config.max_orders and not inflight:
        reason = 'order_limit_reached'
    elif run.estimated_loss_usd + run.pending_estimated_loss_usd > 0 and (
        run.estimated_loss_usd + run.pending_estimated_loss_usd >= config.max_estimated_loss_usd
    ):
        reason = 'estimated_loss_limit_reached'
    elif run.consecutive_errors >= config.max_consecutive_errors:
        reason = 'consecutive_error_limit_reached'
    if reason:
        stop_run_record(session, run, reason)
    return reason


def candidate_rejections(session, run, shipment, checked, bid_rate):
    config = AutopilotSettings.model_validate(run.settings)
    reasons = []
    if not (config.enable_fixed_rate if shipment.order_type == 'fixed_rate' else config.enable_open_bid):
        reasons.append('booking_type_disabled')
    economics = checked.economics
    if economics.gross_profit is None or economics.payout is None or economics.payout <= 0:
        reasons.append('cash_economics_unknown')
    else:
        if economics.gross_profit < config.min_expected_profit_usd:
            reasons.append('autopilot_minimum_profit_not_met')
        if economics.gross_profit * 100 < config.min_expected_margin_pct * economics.payout:
            reasons.append('autopilot_minimum_margin_not_met')
        if (run.estimated_loss_usd + run.pending_estimated_loss_usd + max(-economics.gross_profit, 0)
                > config.max_estimated_loss_usd):
            reasons.append('estimated_loss_budget_exceeded')
    if checked.deadhead_miles is None or checked.deadhead_miles > config.max_deadhead_miles:
        reasons.append('autopilot_deadhead_limit_exceeded_or_unknown')
    if shipment.order_type == 'open_bid' and (bid_rate is None or bid_rate > config.max_bid_rate):
        reasons.append('maximum_bid_exceeded_or_unknown')
    clock = session.get(SimulationClock, 1)
    unit = session.get(FleetUnit, checked.candidate_unit_id) if checked.candidate_unit_id else None
    for name, observed in (
        ('order', shipment.last_synced_at), ('clock', clock.last_synced_at if clock else None),
        ('unit', unit.last_synced_at if unit else None),
    ):
        if observed is None or not -5 <= (wall_now() - utc(observed)).total_seconds() <= config.max_input_age_seconds:
            reasons.append(f'{name}_snapshot_stale_or_unknown')
    return reasons


def authorize_attempt(session, attempt_id, shipment, checked, request):
    """Called inside the guarded action's BEGIN IMMEDIATE transaction."""
    attempt = session.get(AutopilotAttempt, attempt_id)
    if attempt is None or attempt.shipment_id != shipment.shipment_id:
        return ProductError(409, 'Autopilot attempt does not match this order')
    if attempt.action_id is not None:
        return ProductError(409, 'Autopilot attempt already has an action')
    run = session.get(AutopilotRun, attempt.run_id)
    stopped = check_run_limits(session, run)
    config = AutopilotSettings.model_validate(run.settings)
    reasons = []
    if stopped or run.mode != 'live' or attempt.status != 'ready' or attempt.action_id is not None:
        reasons.append('autopilot_not_authorized')
    if run.orders_reserved >= config.max_orders:
        reasons.append('order_limit_reached')
    if attempt.decided_at_wall is None or (wall_now() - utc(attempt.decided_at_wall)).total_seconds() > config.max_decision_age_seconds:
        reasons.append('autopilot_decision_stale')
    bid = getattr(request, 'bid_rate', None)
    expected_decision = 'BID' if shipment.order_type == 'open_bid' else 'ACCEPT'
    if attempt.order_type != shipment.order_type or attempt.decision != expected_decision:
        reasons.append('autopilot_candidate_changed')
    if bid != attempt.bid_rate or checked.candidate_unit_id != attempt.candidate_unit_id:
        reasons.append('autopilot_candidate_changed')
    reasons.extend(candidate_rejections(session, run, shipment, checked, bid))
    attempt.evaluation_snapshot = checked.model_dump(mode='json')
    if reasons:
        attempt.reason_codes = sorted(set(reasons))
        return ProductError(409, 'Autopilot guardrails rejected the action: ' + ', '.join(attempt.reason_codes),
                            evaluation=checked.model_dump(mode='json'))
    return None


def attach_action(session, attempt_id, action_id):
    attempt = session.get(AutopilotAttempt, attempt_id)
    run = session.get(AutopilotRun, attempt.run_id)
    attempt.action_id, attempt.status = action_id, 'submitting'
    run.orders_reserved += 1
    add_activity(session, 'autopilot.action_reserved', 'Autopilot reserved an order-limit slot',
                 shipment_id=attempt.shipment_id, action_id=action_id,
                 details={'run_id': str(run.run_id), 'attempt_id': str(attempt_id), 'orders_reserved': run.orders_reserved})


def before_send(engine, attempt_id, action_id):
    denial = None
    with Session(engine) as session, session.begin():
        session.execute(text('BEGIN IMMEDIATE'))
        attempt = session.get(AutopilotAttempt, attempt_id)
        run = session.get(AutopilotRun, attempt.run_id)
        stopped = check_run_limits(session, run)
        if stopped or attempt.action_id != action_id or attempt.status != 'submitting':
            action = session.get(DispatchAction, action_id)
            action.request_status, action.resolved_at = 'failed', wall_now()
            action.board_message = 'Autopilot stopped before board submission'
            release_resolved_reservations(session)
            denial = ProductError(409, action.board_message)
    if denial:
        raise denial


def stop_running_on_reset(session):
    for run in session.scalars(select(AutopilotRun).where(AutopilotRun.status == 'running')):
        stop_run_record(session, run, 'board_reset')
