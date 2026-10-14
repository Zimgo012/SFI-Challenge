import os
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_database_url() -> str:
    """Read the dispatcher URL without changing the process environment."""
    config = dotenv_values(PROJECT_ROOT / '.env')
    url = os.environ.get('DISPATCHER_DATABASE_URL', config.get('DISPATCHER_DATABASE_URL'))
    return url or f'sqlite:///{PROJECT_ROOT / "dispatcher.db"}'


def create_database_engine(url: str) -> Engine:
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def enable_foreign_keys(connection, connection_record):
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.close()
    return engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_database_engine(get_database_url())


def get_session() -> Iterator[Session]:
    """Use with FastAPI Depends; callers explicitly commit writes."""
    with Session(get_engine()) as session:
        yield session
