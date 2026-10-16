import asyncio
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import logging

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from schema.api import ActionRequest, BidRequest, Page
from schema.autopilot import AutopilotAttemptView, AutopilotRunView, AutopilotSettings
from schema.autopilot_attempt import AutopilotAttempt
from schema.autopilot_run import AutopilotRun
from schema.dispatch_action import DispatchAction
from schema.price_analysis import ModelPriceAdvice, ModelShipmentFeatures
from schema.shipment import Shipment
from service.actions import execute_action
from service.activity import add_activity
from service.autopilot_guards import (
    INFLIGHT, candidate_rejections, check_run_limits, live_enabled, stop_run_record, wall_now,
)
from service.database import get_engine
from service.dispatch_policy import evaluate_dispatch
from service.errors import ProductError
from service.expiration import utc
from service.price_analysis import analysis_settings, make_model_client
from service.ranking import recommendations

logger = logging.getLogger(__name__)


@contextmanager
def transaction(engine):
    if engine.dialect.name != 'sqlite':
        raise ProductError(503, 'Atomic autopilot control currently requires SQLite')
    with Session(engine) as session, session.begin():
        session.execute(text('BEGIN IMMEDIATE'))
        yield session


def run_view(session, run):
    remaining = max(0, (utc(run.deadline_at_wall) - wall_now()).total_seconds()) if run.status == 'running' else 0
    return AutopilotRunView(
        **{field: getattr(run, field) for field in (
            'run_id', 'status', 'mode', 'settings', 'started_at_wall', 'deadline_at_wall',
            'stopped_at_wall', 'stop_reason', 'orders_reserved', 'estimated_loss_usd',
            'pending_estimated_loss_usd', 'consecutive_errors',
        )},
        loss_basis='booking_time_estimates' if run.mode == 'live' else 'shadow_decision_estimates',
        seconds_remaining=remaining,
        inflight_attempt_ids=list(session.scalars(select(AutopilotAttempt.attempt_id).where(
            AutopilotAttempt.run_id == run.run_id, AutopilotAttempt.status.in_(INFLIGHT),
        ))),
        submissions_enabled=run.mode == 'live' and run.status == 'running' and live_enabled(),
    )


def start_run(engine, request):
    settings = AutopilotSettings.model_validate(request.model_dump(exclude={'run_id', 'mode'}))
    try:
        with transaction(engine) as session:
            existing = session.get(AutopilotRun, request.run_id)
            if existing:
                if existing.settings != settings.model_dump(mode='json') or existing.mode != request.mode:
                    raise ProductError(409, 'This run_id already has different settings')
                check_run_limits(session, existing)
                return run_view(session, existing)
            if request.mode == 'live' and not live_enabled():
                raise ProductError(409, 'Live autopilot is disabled; validate shadow runs before enabling AUTOPILOT_LIVE_ENABLED')
            if session.scalar(select(AutopilotRun).where(AutopilotRun.status == 'running')):
                raise ProductError(409, 'An autopilot run is already active; stop it before starting another')
            if request.mode == 'live' and session.scalar(select(AutopilotAttempt.attempt_id).join(
                DispatchAction, DispatchAction.action_id == AutopilotAttempt.action_id,
            ).where(DispatchAction.request_status.in_(('submitting', 'unknown')))):
                raise ProductError(409, 'Reconcile the previous autopilot submission before starting a new live run')
            now = wall_now()
            run = AutopilotRun(
                run_id=request.run_id, mode=request.mode, status='running', settings=settings.model_dump(mode='json'),
                started_at_wall=now, deadline_at_wall=now + timedelta(seconds=settings.max_duration_seconds),
                orders_reserved=0, estimated_loss_usd=0, pending_estimated_loss_usd=0, consecutive_errors=0,
            )
            session.add(run)
            session.flush()
            add_activity(session, 'autopilot.started', f'{run.mode} autopilot started', details={
                'run_id': str(run.run_id), 'settings': run.settings, 'mode': run.mode,
            })
            return run_view(session, run)
    except IntegrityError as exc:
        raise ProductError(409, 'An autopilot run is already active') from exc


def get_run(engine, run_id, *, stop=False):
    with transaction(engine) as session:
        run = session.get(AutopilotRun, run_id)
        if run is None:
            raise ProductError(404, 'Autopilot run not found')
        if stop:
            stop_run_record(session, run, 'user_stopped')
            for attempt in session.scalars(select(AutopilotAttempt).where(
                AutopilotAttempt.run_id == run_id, AutopilotAttempt.status.in_(('evaluating', 'ready')),
                AutopilotAttempt.action_id.is_(None),
            )):
                attempt.status, attempt.finished_at_wall, attempt.reason_codes = 'cancelled', wall_now(), ['user_stopped']
        check_run_limits(session, run)
        session.flush()
        return run_view(session, run)


def list_runs(engine, limit, offset):
    with transaction(engine) as session:
        rows = list(session.scalars(select(AutopilotRun).order_by(AutopilotRun.started_at_wall.desc())))
        for run in rows:
            check_run_limits(session, run)
        return Page(items=[run_view(session, row) for row in rows[offset:offset + limit]], total=len(rows), limit=limit, offset=offset)


def list_attempts(engine, run_id, limit, offset):
    with Session(engine) as session:
        if session.get(AutopilotRun, run_id) is None:
            raise ProductError(404, 'Autopilot run not found')
        rows = list(session.scalars(select(AutopilotAttempt).where(AutopilotAttempt.run_id == run_id).order_by(
            AutopilotAttempt.created_at_wall.desc(), AutopilotAttempt.attempt_id,
        )))
        return Page(items=[AutopilotAttemptView.model_validate(row) for row in rows[offset:offset + limit]],
                    total=len(rows), limit=limit, offset=offset)


def recover_runs(engine, reason='backend_restarted'):
    with transaction(engine) as session:
        for run in session.scalars(select(AutopilotRun).where(AutopilotRun.status == 'running')):
            stop_run_record(session, run, reason)
            for attempt in session.scalars(select(AutopilotAttempt).where(
                AutopilotAttempt.run_id == run.run_id, AutopilotAttempt.status.in_(INFLIGHT),
            )):
                # A committed action may have reached the board. Keep its locks
                # and action status for the ordinary reconciliation pipeline.
                action = session.get(DispatchAction, attempt.action_id) if attempt.action_id else None
                attempt.status = ('submitted' if action.request_status == 'succeeded' else
                                  'rejected' if action.request_status == 'failed' else 'unknown') if action else 'cancelled'
                attempt.reason_codes, attempt.finished_at_wall = [reason], wall_now()


def claim_order(engine):
    with transaction(engine) as session:
        run = session.scalar(select(AutopilotRun).where(AutopilotRun.status == 'running'))
        if run is None or check_run_limits(session, run):
            return None
        config = AutopilotSettings.model_validate(run.settings)
        if session.scalar(select(AutopilotAttempt.attempt_id).where(
            AutopilotAttempt.run_id == run.run_id, AutopilotAttempt.status.in_(INFLIGHT),
        )):
            return None
        if run.last_attempt_at_wall and (wall_now() - utc(run.last_attempt_at_wall)).total_seconds() < config.min_action_interval_seconds:
            return None
        types = [kind for kind, enabled in (('fixed_rate', config.enable_fixed_rate), ('open_bid', config.enable_open_bid)) if enabled]
        attempted = select(AutopilotAttempt.shipment_id).where(AutopilotAttempt.run_id == run.run_id)
        pending = list(session.scalars(select(Shipment).where(
            Shipment.status == 'open', Shipment.board_missing_at.is_(None), Shipment.board_retired_at.is_(None),
            Shipment.order_type.in_(types), Shipment.shipment_id.not_in(attempted),
        ).order_by(Shipment.expires_at, Shipment.external_id)))
        if not pending:
            return None
        by_external_id = {row.external_id: row for row in pending}
        selected = pending[0]
        # Prefer the existing cash/continuity/empty-mile ranking. Only matches
        # compatible with the actual board-style selection can be automated.
        try:
            ranked_items = recommendations(session, limit=200).items
        except ProductError:
            ranked_items = []  # Persist a REVIEW attempt for missing clock/input data.
        for item in ranked_items:
            if item.external_id in by_external_id and item.dispatch_rejection_reasons != ['unit_not_board_selectable']:
                selected = by_external_id[item.external_id]
                break
        now = wall_now()
        attempt = AutopilotAttempt(
            run_id=run.run_id, shipment_id=selected.shipment_id, external_id=selected.external_id,
            order_type=selected.order_type, status='evaluating', created_at_wall=now,
            model_snapshot={}, evaluation_snapshot={}, reason_codes=[],
        )
        run.last_attempt_at_wall = now
        session.add(attempt)
        session.flush()
        add_activity(session, 'autopilot.evaluating', 'Autopilot claimed an order for evaluation',
                     shipment_id=selected.shipment_id, details={'run_id': str(run.run_id), 'attempt_id': str(attempt.attempt_id)})
        return attempt.attempt_id, run.run_id, utc(run.deadline_at_wall)


def candidate_snapshot(engine, attempt_id, bid_rate=None, unit_id=None):
    with Session(engine) as session:
        session.execute(text('BEGIN'))
        attempt = session.get(AutopilotAttempt, attempt_id)
        run = session.get(AutopilotRun, attempt.run_id)
        shipment = session.get(Shipment, attempt.shipment_id)
        checked = evaluate_dispatch(session, shipment, bid_rate, unit_id)
        features = None
        if shipment.order_type == 'open_bid':
            fields = {name: getattr(shipment, name) for name in (
                'distance_miles', 'weight_lbs', 'origin_latitude', 'origin_longitude',
                'destination_latitude', 'destination_longitude', 'origin_state', 'destination_state',
            )}
            for name in ('distance_miles', 'weight_lbs', 'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude'):
                fields[name] = float(fields[name]) if fields[name] is not None else None
            fields['lane_id'] = (f'{shipment.origin_terminal_code}-{shipment.destination_terminal_code}'
                                 if shipment.origin_terminal_code and shipment.destination_terminal_code else None)
            features = ModelShipmentFeatures(**fields).model_dump(mode='json')
        reasons = candidate_rejections(session, run, shipment, checked, bid_rate)
        return checked, reasons, features, AutopilotSettings.model_validate(run.settings)


def store_decision(engine, attempt_id, checked, reasons, *, model=None, bid_rate=None, review=False):
    with transaction(engine) as session:
        attempt = session.get(AutopilotAttempt, attempt_id)
        run = session.get(AutopilotRun, attempt.run_id)
        if check_run_limits(session, run) or attempt.status != 'evaluating':
            if attempt.status == 'evaluating':
                attempt.status, attempt.finished_at_wall = 'cancelled', wall_now()
                attempt.reason_codes = [run.stop_reason or 'autopilot_not_authorized']
            return False
        attempt.candidate_unit_id = checked.candidate_unit_id if checked else None
        attempt.evaluation_snapshot = checked.model_dump(mode='json') if checked else {}
        attempt.model_snapshot, attempt.bid_rate = model or {}, bid_rate
        attempt.reason_codes, attempt.decided_at_wall = list(dict.fromkeys(reasons)), wall_now()
        attempt.decision = ('REVIEW' if review else 'SKIP') if reasons else ('BID' if attempt.order_type == 'open_bid' else 'ACCEPT')
        attempt.status = 'rejected' if reasons else 'ready'
        if reasons:
            attempt.finished_at_wall = wall_now()
            run.consecutive_errors = run.consecutive_errors + 1 if review else 0
        add_activity(session, 'autopilot.decision', f'Autopilot decision: {attempt.decision}', shipment_id=attempt.shipment_id,
                     details={'run_id': str(run.run_id), 'attempt_id': str(attempt_id), 'decision': attempt.decision,
                              'reason_codes': attempt.reason_codes, 'mode': run.mode})
        check_run_limits(session, run)
        return not reasons


def finish_attempt(engine, attempt_id, error=None):
    with transaction(engine) as session:
        attempt = session.get(AutopilotAttempt, attempt_id)
        run = session.get(AutopilotRun, attempt.run_id)
        action = session.get(DispatchAction, attempt.action_id) if attempt.action_id else None
        if action is not None:
            attempt.status = 'submitted' if action.request_status == 'succeeded' else 'rejected' if action.request_status == 'failed' else 'unknown'
        elif attempt.status not in ('cancelled', 'shadow'):
            attempt.status = 'cancelled' if run.status == 'stopped' else 'rejected'
        attempt.finished_at_wall = wall_now()
        if error:
            attempt.message = str(error)[:2000]
            if not attempt.reason_codes:
                attempt.reason_codes = ['action_error']
            if attempt.decision is None:
                attempt.decision = 'REVIEW'
        if attempt.status == 'unknown':
            stop_run_record(session, run, 'submission_outcome_unknown')
        run.consecutive_errors = run.consecutive_errors + 1 if error else 0
        add_activity(session, 'autopilot.attempt_finished', f'Autopilot attempt {attempt.status}',
                     shipment_id=attempt.shipment_id, action_id=attempt.action_id,
                     details={'run_id': str(run.run_id), 'attempt_id': str(attempt_id), 'status': attempt.status})
        check_run_limits(session, run)


def shadow_action(engine, attempt_id):
    with transaction(engine) as session:
        attempt = session.get(AutopilotAttempt, attempt_id)
        run = session.get(AutopilotRun, attempt.run_id)
        config = AutopilotSettings.model_validate(run.settings)
        if check_run_limits(session, run) or attempt.status != 'ready' or run.orders_reserved >= config.max_orders:
            attempt.status, attempt.finished_at_wall = 'cancelled', wall_now()
            return
        attempt.status, attempt.finished_at_wall = 'shadow', wall_now()
        run.orders_reserved += 1
        check_run_limits(session, run)


async def process_one(engine):
    claimed = await asyncio.to_thread(claim_order, engine)
    if claimed is None:
        return False
    attempt_id, run_id, deadline = claimed
    checked, model = None, {}
    try:
        async with asyncio.timeout(max(.001, (deadline - wall_now()).total_seconds())):
            checked, reasons, features, config = await asyncio.to_thread(candidate_snapshot, engine, attempt_id)
            bid = None
            if features is not None:
                operational = [code for code in checked.rejection_reasons
                               if next(item.check for item in checked.rejection_details if item.code == code) != 'pricing_passed']
                operational.extend(code for code in reasons if code not in ('cash_economics_unknown', 'maximum_bid_exceeded_or_unknown'))
                if operational or checked.economics.total_cost is None:
                    reasons = operational or ['cash_economics_unknown']
                else:
                    url, timeout, _ = analysis_settings()
                    async with asyncio.timeout(timeout), make_model_client(url, timeout) as client:
                        response = await client.post('api/v1/predict-bid', json=features)
                    response.raise_for_status()
                    data = response.json()
                    json.dumps(data, allow_nan=False)
                    model = {'request': features, 'response': data,
                             'prediction_id': response.headers.get('X-Prediction-Id')}
                    advice = ModelPriceAdvice.model_validate(data)
                    if advice.pricing_source == 'baseline' and not config.allow_baseline:
                        reasons = ['baseline_not_enabled']
                    else:
                        bid = Decimal(str(advice.predicted_bid_dollars)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                        if bid <= 0:
                            raise ValueError('Model price rounded to zero')
                        checked, reasons, _, _ = await asyncio.to_thread(
                            candidate_snapshot, engine, attempt_id, bid, checked.candidate_unit_id,
                        )
                        reasons = [*checked.rejection_reasons, *reasons]
            else:
                reasons = [*checked.rejection_reasons, *reasons]
            ready = await asyncio.to_thread(store_decision, engine, attempt_id, checked, reasons,
                                           model=model, bid_rate=bid,
                                           review=any('unknown' in code or 'stale' in code or 'baseline' in code for code in reasons))
            if not ready:
                return True
            with Session(engine) as session:
                attempt = session.get(AutopilotAttempt, attempt_id)
                run = session.get(AutopilotRun, run_id)
                mode, external_id, kind = run.mode, attempt.external_id, attempt.order_type
            if mode == 'shadow':
                await asyncio.to_thread(shadow_action, engine, attempt_id)
            else:
                request = BidRequest(bid_rate=bid, carrier_note=f'autopilot:{run_id}') if kind == 'open_bid' else ActionRequest(carrier_note=f'autopilot:{run_id}')
                await execute_action(engine, external_id, 'bid' if kind == 'open_bid' else 'accept', request,
                                     autopilot_attempt_id=attempt_id)
                await asyncio.to_thread(finish_attempt, engine, attempt_id)
    except asyncio.CancelledError:
        await asyncio.shield(asyncio.to_thread(recover_runs, engine, 'backend_shutdown'))
        raise
    except TimeoutError:
        if wall_now() >= deadline:
            with transaction(engine) as session:
                stop_run_record(session, session.get(AutopilotRun, run_id), 'time_limit_reached')
            await asyncio.to_thread(finish_attempt, engine, attempt_id, 'Autopilot time limit reached')
        else:
            await asyncio.to_thread(store_decision, engine, attempt_id, checked, ['MODEL_TIMEOUT'], model=model, review=True)
    except ProductError as exc:
        await asyncio.to_thread(finish_attempt, engine, attempt_id, exc.detail)
    except Exception as exc:
        with Session(engine) as session:
            status = session.get(AutopilotAttempt, attempt_id).status
        if status == 'evaluating':
            await asyncio.to_thread(store_decision, engine, attempt_id, checked,
                                   [f'evaluation_error:{type(exc).__name__}'], model=model, review=True)
        else:
            await asyncio.to_thread(finish_attempt, engine, attempt_id, type(exc).__name__)
    return True


async def autopilot_worker():
    while True:
        await asyncio.sleep(1)
        try:
            await process_one(get_engine())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Autopilot worker failed; no unguarded submission is attempted')
