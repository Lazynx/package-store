from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OrderStatus(Enum):
    CREATED = 'created'
    PENDING_PAYMENT = 'pending_payment'
    PAID = 'paid'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class PackageType(Enum):
    BASIC = 'basic'
    STANDARD = 'standard'
    PREMIUM = 'premium'


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    package_type: Mapped[PackageType] = mapped_column(SQLEnum(PackageType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='usd', nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.CREATED,
        nullable=False,
    )

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True
    )
    stripe_client_secret: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f'Order(id={self.id}, status={self.status}, amount={self.amount})'

class WebhookEvent(Base):
    __tablename__ = 'webhook_events'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    stripe_event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    order_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)

    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f'<WebhookEvent(id={self.id}, event_type={self.event_type}, processed={self.processed})>'


class PaymentAudit(Base):
    __tablename__ = 'payment_audit'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_status: Mapped[OrderStatus | None] = mapped_column(
        SQLEnum(OrderStatus, name='order_status', create_constraint=True),
        nullable=True
    )
    new_status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name='order_status', create_constraint=True),
        nullable=False
    )

    stripe_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f'<PaymentAudit(order_id={self.order_id}, action={self.action})>'
