import asyncio
from decimal import Decimal
from urllib.parse import quote

import httpx
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from schema.board_api import BoardOrder
from schema.shipment import Shipment


def known_order_ids(engine: Engine) -> set[str]:
    with Session(engine) as session:
        return set(session.scalars(select(Shipment.external_id)))


async def reconcile_known_orders(
    client: httpx.AsyncClient, engine: Engine, snapshot: list[BoardOrder],
) -> tuple[list[BoardOrder], set[str]]:
    """Recover known orders outside the board's capped status=all response."""
    known_ids = await asyncio.to_thread(known_order_ids, engine)
    absent_ids = known_ids - {order.external_id for order in snapshot}
    semaphore = asyncio.Semaphore(8)

    async def fetch_order(external_id: str) -> tuple[str, BoardOrder | None]:
        async with semaphore:
            response = await client.get('orders/' + quote(external_id, safe=''))
            if response.status_code == 404:
                return external_id, None
            response.raise_for_status()
            order = BoardOrder.model_validate(response.json(parse_float=Decimal))
            if order.external_id != external_id:
                raise ValueError('Board returned a different external_id during reconciliation')
            return external_id, order

    results = await asyncio.gather(*(fetch_order(external_id) for external_id in sorted(absent_ids)))
    recovered = [order for _, order in results if order is not None]
    missing_ids = {external_id for external_id, order in results if order is None}
    return [*snapshot, *recovered], missing_ids
