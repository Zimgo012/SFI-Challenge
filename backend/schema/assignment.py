from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from schema.base import Base


class Assignment(Base):
    __tablename__ = 'assignments'

    assignment_id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    shipment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey('shipments.shipment_id'),
        index=True,
        unique=True,
        nullable=False,
    )
    unit_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey('fleet_units.unit_id'),
        index=True,
        nullable=False,
    )
    origin_terminal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey('terminals.terminal_id'),
        index=True,
        nullable=False,
    )
    destination_terminal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey('terminals.terminal_id'),
        index=True,
        nullable=False,
    )
    busy_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    busy_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assignment_status: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
