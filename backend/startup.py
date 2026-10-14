import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from service.ingest import ingest as call_external_api

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parent / '.env'


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run initialization before the application accepts requests."""
    load_dotenv(ENV_FILE, override=False)
    external_api_url = os.getenv('EXTERNAL_API_URL', '').strip()

    if external_api_url:
        await call_external_api(external_api_url)
    else:
        logger.info('EXTERNAL_API_URL is unset; skipping external API startup hook.')

    yield
