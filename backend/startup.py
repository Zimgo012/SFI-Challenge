import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from service.ingest import ingest as call_external_api
from service.order_stream import consume_orders
from service.expiration import monitor_expirations
from service.system_state import connection_state

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parent / '.env'


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run initialization before the application accepts requests."""
    load_dotenv(ENV_FILE, override=False)
    external_api_url = os.getenv('EXTERNAL_API_URL', '').strip()

    orders_task = None
    expiration_task = None
    if external_api_url:
        connection_state.set('connecting')
        await call_external_api(external_api_url)
        orders_task = asyncio.create_task(consume_orders(external_api_url), name='board-orders')
        app.state.orders_task = orders_task
        expiration_task = asyncio.create_task(monitor_expirations(), name='offer-expirations')
        app.state.expiration_task = expiration_task
    else:
        connection_state.set('disabled')
        logger.info('EXTERNAL_API_URL is unset; skipping external API startup hook.')

    try:
        yield
    finally:
        tasks = [task for task in (orders_task, expiration_task) if task is not None]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
