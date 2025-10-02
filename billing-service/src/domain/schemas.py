from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from infrastructure.models import OrderStatus, PackageType


class PackageInfo(BaseModel):
    type: PackageType
    name: str
    description: str
    price: Decimal
    currency: str = 'USD'
    features: list[str]



class OrderCreate(BaseModel):
    package_type: PackageType
    metadata: dict | None = None


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    package_type: PackageType
    amount: Decimal
    currency: str
    description: str | None
    status: OrderStatus
    stripe_payment_intent_id: str | None
    stripe_client_secret: str | None
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page: int
    page_size: int



class PaymentIntentResponse(BaseModel):
    order_id: UUID
    client_secret: str
    amount: Decimal
    currency: str
    status: OrderStatus


class PaymentConfirmation(BaseModel):
    order_id: UUID
    payment_intent_id: str



class StripeWebhookEvent(BaseModel):
    id: str
    type: str
    data: dict
    created: int



class OrderCreatedEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    package_type: PackageType
    amount: Decimal
    currency: str
    created_at: datetime

    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat(),
        Decimal: lambda v: str(v),
        UUID: lambda v: str(v),
    })


class OrderPaidEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    package_type: PackageType
    amount: Decimal
    currency: str
    paid_at: datetime
    stripe_payment_intent_id: str

    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat(),
        Decimal: lambda v: str(v),
        UUID: lambda v: str(v),
    })


class OrderFailedEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    reason: str
    failed_at: datetime

    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat(),
        UUID: lambda v: str(v),
    })



class OrderStats(BaseModel):
    total_orders: int
    paid_orders: int
    failed_orders: int
    total_revenue: Decimal
    currency: str = 'USD'


class WebhookEventResponse(BaseModel):
    id: UUID
    stripe_event_id: str
    event_type: str
    order_id: UUID | None
    processed: bool
    created_at: datetime
    processed_at: datetime | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)
