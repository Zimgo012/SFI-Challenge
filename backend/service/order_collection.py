"""Collect order identities without reserving trucks or calling a model."""
from datetime import datetime, timedelta

from sqlalchemy import select

from schema.allocation_plan import AllocationPlan
from schema.autopilot import AutopilotSettings
from schema.autopilot_run import AutopilotRun
from schema.simulation_clock import SimulationClock
from service.activity import add_activity
from service.autopilot_guards import wall_now
from service.expiration import simulated_now, utc


def observe_orders(session, orders, *, observed_at=None):
    """Called in ingestion's transaction; a late worker cannot extend the window."""
    now = observed_at or wall_now()
    rows = session.execute(select(AllocationPlan, AutopilotRun).join(AutopilotRun).where(
        AllocationPlan.status == 'collecting', AutopilotRun.status == 'running')).all()
    for plan, run in rows:
        collection = plan.result['collection']
        if not (utc(datetime.fromisoformat(collection['started_at_wall'])) <= now
                < utc(datetime.fromisoformat(collection['closes_at_wall']))):
            continue
        config = AutopilotSettings.model_validate(run.settings)
        types = {kind for kind, enabled in (('fixed_rate', config.enable_fixed_rate),
                                           ('open_bid', config.enable_open_bid)) if enabled}
        ids = set(collection['observed_external_ids'])
        ids.update(order.external_id for order in orders if order.status == 'open'
                   and order.order_type in types and order.board_missing_at is None and order.board_retired_at is None)
        if ids != set(collection['observed_external_ids']):
            plan.result = plan.result | {'collection': collection | {'observed_external_ids': sorted(ids)}}


def collecting_plan(session, run_id):
    return session.scalar(select(AllocationPlan).where(AllocationPlan.run_id == run_id,
                                                       AllocationPlan.status == 'collecting'))


def open_collected_orders(session, plan, run):
    from service.fleet_allocation import available_orders
    ids = plan.result['collection']['observed_external_ids']
    config = AutopilotSettings.model_validate(run.settings)
    clock = session.get(SimulationClock, 1)
    if clock is None:
        return []
    sim = simulated_now(clock, wall_now())
    return [order for order in available_orders(session, config, ids, run.run_id)
            if order.expires_at is not None and utc(order.expires_at) > sim]


def collect_or_close(session, run, config, now):
    """Return a frozen-ID planning batch only after the wall-clock window closes."""
    from service.fleet_allocation import available_orders
    plan = collecting_plan(session, run.run_id)
    if plan is None:
        orders = available_orders(session, config, run_id=run.run_id)
        if not orders:
            return None
        closes = min(utc(run.deadline_at_wall), now + timedelta(seconds=config.collection_window_seconds))
        collection = {'started_at_wall': now.isoformat(), 'closes_at_wall': closes.isoformat(),
                      'window_seconds': config.collection_window_seconds, 'time_basis': 'wall_clock_utc',
                      'observed_external_ids': sorted(order.external_id for order in orders)}
        plan = AllocationPlan(run_id=run.run_id, status='collecting', result={'collection': collection},
                              created_at_wall=now, expires_at_wall=closes)
        session.add(plan)
        session.flush()
        plan.result = {'collection': collection | {'root_plan_id': str(plan.plan_id)}}
        add_activity(session, 'autopilot.collection_started', 'Collecting open orders',
                     details={'plan_id': str(plan.plan_id), 'closes_at_wall': closes.isoformat()})
        return None
    if now < utc(datetime.fromisoformat(plan.result['collection']['closes_at_wall'])):
        # Arrival ingestion also observes IDs, so orders arriving between ticks
        # are captured without depending on the worker's polling cadence.
        observe_orders(session, available_orders(session, config, run_id=run.run_id), observed_at=now)
        return None
    collection = plan.result['collection']
    ids = sorted(order.external_id for order in open_collected_orders(session, plan, run))
    plan.result = plan.result | {'collection': collection | {
        'closed_at_wall': now.isoformat(), 'eligible_external_ids': ids,
        'excluded_external_ids': sorted(set(collection['observed_external_ids']) - set(ids)),
    }}
    plan.status = 'planning'
    plan.expires_at_wall = min(utc(run.deadline_at_wall), now + timedelta(seconds=120))
    run.last_attempt_at_wall = now
    add_activity(session, 'autopilot.collection_closed', 'Open-order collection closed',
                 details={'plan_id': str(plan.plan_id), 'observed_count': len(collection['observed_external_ids']),
                          'eligible_count': len(ids)})
    return plan


def continue_collection(session, run, config, now):
    """Recheck remaining selected work from a closed cohort without collecting again."""
    from service.fleet_allocation import available_orders
    previous = session.scalar(select(AllocationPlan).where(AllocationPlan.run_id == run.run_id).order_by(
        AllocationPlan.created_at_wall.desc(), AllocationPlan.plan_id.desc()))
    if previous is None or 'collection' not in previous.result:
        return None
    selected = [row['external_id'] for row in previous.result.get('selected', [])]
    if not selected:
        return None
    clock = session.get(SimulationClock, 1)
    if clock is None:
        return None
    sim = simulated_now(clock, now)
    remaining = [order.external_id for order in available_orders(session, config, selected, run.run_id)
                 if order.expires_at is not None and utc(order.expires_at) > sim]
    if not remaining:
        return None
    plan = AllocationPlan(run_id=run.run_id, status='planning', created_at_wall=now,
        expires_at_wall=min(utc(run.deadline_at_wall), now + timedelta(seconds=120)),
        result={'collection': previous.result['collection'] | {
            'remaining_external_ids': sorted(remaining), 'continued_from_plan_id': str(previous.plan_id)}})
    session.add(plan)
    run.last_attempt_at_wall = now
    session.flush()
    add_activity(session, 'autopilot.collection_continued', 'Rechecking remaining selected orders',
                 details={'plan_id': str(plan.plan_id), 'root_plan_id': previous.result['collection']['root_plan_id'],
                          'remaining_count': len(remaining)})
    return plan


def collection_view(session, run):
    plan = collecting_plan(session, run.run_id)
    if plan is None:
        return dict(collection_plan_id=None, collection_seconds_remaining=0, collected_order_count=0)
    closes = utc(datetime.fromisoformat(plan.result['collection']['closes_at_wall']))
    return dict(collection_plan_id=plan.plan_id, collection_seconds_remaining=max(0, (closes - wall_now()).total_seconds()),
                collected_order_count=len(open_collected_orders(session, plan, run)))
