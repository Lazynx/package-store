from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderCreatedEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    package_type: str
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
    package_type: str
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
