import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone

import anyio
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from schema.load_stream import LoadStreamMessage, LoadStreamState
from schema.shipment import Shipment
from service.dashboard import load_view, system_status
from service.expiration import utc

logger = logging.getLogger('uvicorn.error.loads')
CHECK_INTERVAL_SECONDS = 0.5
HEARTBEAT_SECONDS = 30
SEND_TIMEOUT_SECONDS = 10


def read_loads(engine: Engine, order_type: str, status: str, origin_terminal: str | None) -> LoadStreamState:
    # Short local reads see committed ingestion from every backend worker.
    # Subscribers never create additional connections to the external board.
    with Session(engine) as session:
        system = system_status(session)
        statement = select(Shipment).where(Shipment.board_missing_at.is_(None)).order_by(
            Shipment.board_created_at.desc(), Shipment.external_id,
        )
        if order_type != 'all':
            statement = statement.where(Shipment.order_type == order_type)
        if origin_terminal:
            statement = statement.where(func.upper(Shipment.origin_terminal_code) == origin_terminal.upper())
        items = []
        for row in session.scalars(statement):
            view = load_view(row, system.sim_time_utc)
            # Do not advertise an expired offer between background expiration ticks.
            if (row.status == 'open' and row.expires_at is not None
                    and system.sim_time_utc is not None and utc(row.expires_at) <= system.sim_time_utc):
                view.status = 'expired'
                view.seconds_remaining = 0
                view.estimated_profit = None
                view.profit_category = 'unavailable'
            if status == 'all' or view.status == status:
                items.append(view)
        return LoadStreamState(items=items, system=system)


def fingerprint(state: LoadStreamState) -> str:
    # Countdown progression alone waits for a heartbeat. The frontend can advance
    # countdowns using system.sim_time_utc, simulation_speed, and its elapsed time.
    return state.model_dump_json(exclude={
        'items': {'__all__': {'seconds_remaining', 'last_synced_at'}},
        'system': {'sim_time_utc', 'last_sync_at'},
    })


async def stream_loads(
    websocket: WebSocket, engine: Engine, *, order_type: str = 'open_bid',
    status: str = 'open', origin_terminal: str | None = None,
) -> None:
    await websocket.accept()

    async def send_updates():
        previous = None
        revision = 0
        last_sent = 0
        loop = asyncio.get_running_loop()
        while True:
            state = await asyncio.to_thread(read_loads, engine, order_type, status, origin_terminal)
            current = fingerprint(state)
            event = None
            if previous is None:
                event = 'loads.snapshot'
            elif current != previous:
                event = 'loads.updated'
            elif loop.time() - last_sent >= HEARTBEAT_SECONDS:
                event = 'loads.heartbeat'
            if event:
                revision += 1
                message = LoadStreamMessage(
                    **state.model_dump(), event=event, revision=revision,
                    sent_at=datetime.now(timezone.utc),
                )
                await asyncio.wait_for(websocket.send_json(message.model_dump(mode='json')), SEND_TIMEOUT_SECONDS)
                previous = current
                last_sent = loop.time()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def receive_disconnect():
        while True:
            if (await websocket.receive())['type'] == 'websocket.disconnect':
                return

    tasks = [asyncio.create_task(send_updates()), asyncio.create_task(receive_disconnect())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, OSError):
        pass
    except Exception:
        logger.exception('Live load stream failed')
        with suppress(Exception):
            await asyncio.wait_for(websocket.send_json({
                'event': 'loads.error', 'message': 'Live orders are temporarily unavailable',
            }), SEND_TIMEOUT_SECONDS)
            await websocket.close(code=1011)
    finally:
        for task in tasks:
            task.cancel()
        with anyio.CancelScope(shield=True):
            await asyncio.gather(*tasks, return_exceptions=True)
