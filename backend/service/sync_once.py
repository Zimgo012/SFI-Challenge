"""Run one authoritative board reconciliation and changed-CSV import."""
import asyncio
import json

from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from schema.fleet_unit import FleetUnit
from schema.historical_shipment import HistoricalShipment
from schema.shipment import Shipment
from schema.terminal import Terminal
from service.actions import board_url
from service.database import PROJECT_ROOT, get_engine
from service.history_import import sync_history_if_changed
from service.ingest import ingest


async def main():
    load_dotenv(PROJECT_ROOT / '.env', override=False)
    history = await asyncio.to_thread(sync_history_if_changed)
    orders = await ingest(board_url())
    with Session(get_engine()) as session:
        counts = {model.__tablename__: session.scalar(select(func.count()).select_from(model))
                  for model in (Terminal, FleetUnit, Shipment, HistoricalShipment)}
    print(json.dumps({'history_import': history, 'orders_reconciled': len(orders), 'stored_counts': counts}))


if __name__ == '__main__':
    asyncio.run(main())
