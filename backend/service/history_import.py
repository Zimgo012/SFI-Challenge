import csv
import hashlib
import io
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from schema.activity import Activity
from schema.historical_shipment import HistoricalShipment
from schema.history_import import HistoricalCsvRow
from service.activity import add_activity
from service.database import PROJECT_ROOT, get_engine
from service.ingest import upsert


def configured_history_path():
    config = dotenv_values(PROJECT_ROOT / '.env')
    value = os.environ.get('HISTORY_CSV_PATH', config.get('HISTORY_CSV_PATH', ''))
    if not value or not value.strip():
        return None
    path = Path(value.strip()).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def sync_history_if_changed(engine=None, path=None):
    """Import the configured CSV atomically; unchanged bytes require no row writes."""
    path = Path(path) if path is not None else configured_history_path()
    if path is None:
        return {'enabled': False, 'imported': False, 'rows': 0}
    data = path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    engine = engine if engine is not None else get_engine()
    with Session(engine) as session, session.begin():
        if engine.dialect.name == 'sqlite':
            session.execute(text('BEGIN IMMEDIATE'))
        previous = session.scalar(select(Activity).where(Activity.event_type == 'history.imported').order_by(
            Activity.occurred_at_wall.desc(), Activity.event_id.desc(),
        ))
        if previous and previous.details.get('sha256') == checksum:
            return {'enabled': True, 'imported': False, 'rows': previous.details['rows'], 'sha256': checksum}
        reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))
        required = {field.alias or name for name, field in HistoricalCsvRow.model_fields.items() if field.is_required()}
        required.discard('source_record_key')
        required.add('shipment_id')
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('Historical CSV is missing required columns: ' + ', '.join(sorted(required - set(reader.fieldnames or []))))
        rows = []
        keys = set()
        for number, raw in enumerate(reader, 2):
            if None in raw:
                raise ValueError(f'Invalid historical CSV row {number}: too many columns')
            try:
                row = HistoricalCsvRow.model_validate({key: (None if value == '' else value) for key, value in raw.items()})
            except ValueError as exc:
                raise ValueError(f'Invalid historical CSV row {number}: {exc}') from exc
            key = 'csv:' + row.source_record_key
            if key in keys:
                raise ValueError(f'Duplicate historical shipment ID at row {number}')
            keys.add(key)
            rows.append(row.model_dump() | {'source_record_key': key})
        if not rows:
            raise ValueError('Historical CSV has no data rows; existing history was preserved')
        for row in rows:
            upsert(session, HistoricalShipment, 'source_record_key', row)
        # This CSV is an authoritative dataset; retain unrelated/manual sources.
        existing = session.scalars(select(HistoricalShipment.source_record_key).where(
            HistoricalShipment.source_record_key.like('csv:%'),
        )).all()
        removed = set(existing) - keys
        if removed:
            session.execute(delete(HistoricalShipment).where(HistoricalShipment.source_record_key.in_(removed)))
        add_activity(session, 'history.imported', f'Imported {len(rows)} historical shipments', details={
            'source': str(path), 'sha256': checksum, 'rows': len(rows), 'removed': len(removed),
        })
        return {'enabled': True, 'imported': True, 'rows': len(rows), 'sha256': checksum}
