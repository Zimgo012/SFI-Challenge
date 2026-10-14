from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from schema.base import Base


class Shipment(Base):
    __tablename__ = 'shipments'

    shipment_id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    board_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    order_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    origin_terminal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_terminal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_terminal_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey('terminals.terminal_id'),
        index=True,
        nullable=True,
    )
    destination_terminal_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey('terminals.terminal_id'),
        index=True,
        nullable=True,
    )
    origin_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    origin_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    destination_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    destination_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    distance_miles: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    weight_lbs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offered_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    cost_per_mile: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    estimated_deadhead_miles: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    estimated_deadhead_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    estimated_total_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    board_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    bid_decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    winning_bid_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    board_assigned_unit_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assigned_terminal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
