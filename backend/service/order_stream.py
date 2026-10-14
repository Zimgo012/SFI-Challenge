import asyncio
import json
import logging
import os
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

from websockets.asyncio.client import connect

from schema.board_event import BoardEvent
from service.database import get_engine
from service.ingest import ingest, persist_orders
from service.activity import record_system_event
from service.system_state import connection_state

# Inherit Uvicorn's console handler so temporary order logs are visible locally.
logger = logging.getLogger('uvicorn.error.orders')


def websocket_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        raise ValueError('EXTERNAL_API_URL must be an absolute HTTP(S) base URL')
    scheme = 'wss' if parts.scheme == 'https' else 'ws'
    return urlunsplit((scheme, parts.netloc, parts.path.rstrip('/') + '/orders/ws', '', ''))


def log_orders(event: str, orders) -> None:
    if os.getenv('LOG_LIVE_ORDERS', 'true').lower() not in ('0', 'false', 'no', 'off'):
        verbose = os.getenv('LOG_LIVE_ORDERS_VERBOSE', 'false').strip().lower() in (
            '1', 'true', 'yes', 'on',
        )
        fields = {
            'external_id', 'status', 'origin_longitude', 'origin_latitude',
            'destination_longitude', 'destination_latitude',
        }
        payloads = [
            order.model_dump(exclude_unset=True) if verbose else order.model_dump(include=fields)
            for order in orders
        ]
        logger.info(
            'Live orders event=%s orders=%s', event,
            json.dumps(payloads, default=str),
        )


async def handle_event(message: str | bytes, base_url: str) -> None:
    event = BoardEvent.model_validate(json.loads(message, parse_float=Decimal))
    orders = event.orders or ([event.order] if event.order is not None else [])
    if event.event == 'snapshot':
        # A full HTTP sync runs after connecting. The queued open-only snapshot
        # may be older, so log it without overwriting that authoritative sync.
        log_orders(event.event, orders)
        return
    if event.event == 'lifecycle':
        logger.info('Board lifecycle change: %s; refreshing board state', event.stats)
        # The board sends counts rather than the changed order payloads.
        refreshed_orders = await ingest(base_url)
        log_orders(event.event, refreshed_orders)
        return
    if event.order is not None or event.orders is not None:
        await asyncio.to_thread(
            persist_orders, get_engine(), orders, event.clock,
            created_only=event.event == 'order.created',
        )
        log_orders(event.event, orders)
        if event.event == 'order.created' or any(
            order.status in ('accepted', 'in_transit', 'completed') for order in orders
        ):
            # New arrivals also serve as reconciliation checkpoints if a
            # lifecycle message was missed while the socket stayed connected.
            await ingest(base_url)
        return
    logger.warning('Ignoring unsupported board event: %s', event.event)


async def consume_orders(base_url: str) -> None:
    """Listen continuously; reconnect and reconcile missed changes after failures."""
    url = websocket_url(base_url)
    retry_delay = 1
    while True:
        try:
            connection_state.set('connecting')
            async with connect(
                url, open_timeout=10, close_timeout=5,
                ping_interval=20, ping_timeout=20, max_size=4 * 1024 * 1024,
            ) as websocket:
                # Subscribe first: messages buffer while the fresh HTTP sync runs,
                # closing the gap between recovery and consuming new arrivals.
                await ingest(base_url)
                retry_delay = 1
                connection_state.set('connected')
                logger.info('Order WebSocket connected; fresh board sync complete')
                async for message in websocket:
                    await handle_event(message, base_url)
            logger.warning('Order WebSocket closed; reconnecting in %ss', retry_delay)
            connection_state.set('reconnecting')
        except asyncio.CancelledError:
            connection_state.set('disconnected')
            raise
        except Exception as exc:
            connection_state.set('reconnecting', type(exc).__name__)
            logger.exception('Order stream failed; reconnecting in %ss', retry_delay)
            try:
                await asyncio.to_thread(record_system_event, get_engine(), 'stream.error', type(exc).__name__)
            except Exception:
                logger.exception('Could not record stream failure in activity history')
        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 30)
