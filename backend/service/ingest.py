import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from pydantic import TypeAdapter
from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from schema.board_api import BoardClock, BoardFleetSnapshot, BoardOrder, BoardTerminal
from schema.dispatcher import FleetUnit, Shipment, SimulationClock, Terminal
from service.database import get_engine
from service.expiration import expire_due_offers
from service.reconciliation import reconcile_known_orders
from service.fleet import log_discrepancies, reconcile_fleet, validate_roster

logger = logging.getLogger(__name__)


def upsert(
    session: Session, model, key: str, values: dict, *, insert_only: bool = False,
) -> None:
    """Preserve local primary keys while updating the board-owned fields."""
    dialect = session.get_bind().dialect.name
    insert = {'sqlite': sqlite_insert, 'postgresql': postgres_insert}.get(dialect)
    if insert is None:
        raise ValueError(f'Board ingestion does not support database dialect {dialect}')
    statement = insert(model).values(**values)
    if insert_only:
        statement = statement.on_conflict_do_nothing(index_elements=[key])
    else:
        statement = statement.on_conflict_do_update(
            index_elements=[key],
            set_={name: getattr(statement.excluded, name) for name in values if name != key},
        )
    session.execute(statement)


def upsert_orders(
    session: Session, orders: list[BoardOrder], synced_at: datetime,
    *, created_only: bool = False,
) -> None:
    terminals_by_code = {
        row.code.upper(): row.terminal_id for row in session.scalars(select(Terminal))
    }
    for order in orders:
        values = order.model_dump(
            exclude={'id', 'created_at', 'assigned_driver_id'}, exclude_unset=True,
        )
        values.update(board_order_id=order.id, last_synced_at=synced_at, board_missing_at=None)
        if 'created_at' in order.model_fields_set:
            values['board_created_at'] = order.created_at
        if 'assigned_driver_id' in order.model_fields_set:
            values['board_assigned_unit_id'] = order.assigned_driver_id
        for side in ('origin', 'destination'):
            code = getattr(order, f'{side}_terminal_code')
            if f'{side}_terminal_code' in order.model_fields_set:
                values[f'{side}_terminal_id'] = terminals_by_code.get((code or '').upper())
        upsert(session, Shipment, 'external_id', values, insert_only=created_only)


def persist_orders(
    engine: Engine, orders: list[BoardOrder], clock: BoardClock | None = None,
    *, created_only: bool = False,
) -> None:
    synced_at = datetime.now(timezone.utc)
    with Session(engine) as session, session.begin():
        upsert_orders(session, orders, synced_at, created_only=created_only)
        if clock is not None:
            stored_clock = session.get(SimulationClock, 1)
            previous_wall_time = (
                stored_clock.wall_time_utc.replace(tzinfo=timezone.utc)
                if stored_clock is not None else None
            )
            if previous_wall_time is None or clock.wall_time_utc >= previous_wall_time:
                upsert(session, SimulationClock, 'clock_id', {
                    'clock_id': 1, **clock.model_dump(), 'last_synced_at': synced_at,
                })
        expire_due_offers(session)


def persist_snapshot(
    engine: Engine,
    terminals: list[BoardTerminal],
    fleet: list[BoardFleetSnapshot],
    clock: BoardClock,
    orders: list[BoardOrder],
    *, clock_received_at: datetime | None = None,
    missing_order_ids: set[str] | None = None,
) -> None:
    validate_roster(fleet)
    synced_at = datetime.now(timezone.utc)
    with Session(engine) as session, session.begin():
        # Include roster terminals in case a terminal was added between API reads.
        for terminal in [*terminals, *(snapshot.terminal for snapshot in fleet)]:
            values = terminal.model_dump(exclude={'id', 'unit_capacity'})
            values.update(
                board_terminal_id=terminal.id,
                seeded_unit_capacity=terminal.unit_capacity,
                last_synced_at=synced_at,
            )
            upsert(session, Terminal, 'board_terminal_id', values)

        terminal_rows = session.scalars(select(Terminal)).all()
        terminals_by_board_id = {row.board_terminal_id: row.terminal_id for row in terminal_rows}

        for snapshot in fleet:
            for unit in snapshot.units:
                terminal_id = terminals_by_board_id.get(unit.home_terminal_id)
                if terminal_id is None:
                    raise ValueError(f'Fleet unit {unit.id} references an unknown terminal')
                values = unit.model_dump(exclude={'id', 'home_terminal_id'})
                values.update(
                    board_unit_id=unit.id,
                    home_terminal_id=terminal_id,
                    last_synced_at=synced_at,
                    board_missing_at=None,
                )
                upsert(session, FleetUnit, 'board_unit_id', values)

        upsert_orders(session, orders, synced_at)
        if missing_order_ids:
            session.execute(
                update(Shipment)
                .where(Shipment.external_id.in_(missing_order_ids))
                .values(board_missing_at=func.coalesce(Shipment.board_missing_at, synced_at))
            )

        upsert(session, SimulationClock, 'clock_id', {
            'clock_id': 1,
            **clock.model_dump(),
            'last_synced_at': clock_received_at or synced_at,
        })
        expire_due_offers(session)
        capacity = reconcile_fleet(session, fleet, clock.sim_time_utc, synced_at)
    log_discrepancies(capacity)


async def ingest(
    external_api_url: str,
    *,
    engine: Engine | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[BoardOrder]:
    """Fetch and validate board state, then atomically upsert it locally."""
    clock_received_at = None
    engine = engine if engine is not None else get_engine()
    async with httpx.AsyncClient(
        base_url=external_api_url.rstrip('/') + '/', timeout=20.0, transport=transport,
    ) as client:
        async def fetch(path: str):
            nonlocal clock_received_at
            response = await client.get(path)
            response.raise_for_status()
            if path == 'simulation/clock':
                clock_received_at = datetime.now(timezone.utc)
            return response.json(parse_float=Decimal)

        terminals_data, orders_data = await asyncio.gather(
            fetch('terminals'), fetch('orders?status=all'),
        )
        orders = TypeAdapter(list[BoardOrder]).validate_python(orders_data)
        orders, missing_order_ids = await reconcile_known_orders(client, engine, orders)
        # Order reads can advance delivery lifecycle on the board. Refresh the
        # roster afterwards so position, availability, and re-homing are current.
        fleet_data, clock_data = await asyncio.gather(
            fetch('fleet/snapshot'), fetch('simulation/clock'),
        )

    terminals = TypeAdapter(list[BoardTerminal]).validate_python(terminals_data)
    fleet = TypeAdapter(list[BoardFleetSnapshot]).validate_python(fleet_data)
    clock = BoardClock.model_validate(clock_data)
    await asyncio.to_thread(
        persist_snapshot, engine,
        terminals, fleet, clock, orders, clock_received_at=clock_received_at,
        missing_order_ids=missing_order_ids,
    )
    logger.info(
        'Board sync complete: %d terminals, %d units, %d orders; simulated time %s',
        len(terminals), sum(len(snapshot.units) for snapshot in fleet), len(orders),
        clock.sim_time_utc.isoformat(),
    )
    if missing_order_ids:
        logger.warning(
            '%d locally retained orders are absent from the board; history preserved',
            len(missing_order_ids),
        )
    return orders
