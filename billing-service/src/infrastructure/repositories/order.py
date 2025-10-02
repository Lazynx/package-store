from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.models import (
    Order,
    OrderStatus,
    PackageType,
    PaymentAudit,
    WebhookEvent,
)


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: UUID,
        package_type: PackageType,
        amount: Decimal,
        currency: str = 'USD',
        description: str | None = None,
        metadata: str | None = None,
    ) -> Order:
        order = Order(
            user_id=user_id,
            package_type=package_type,
            amount=amount,
            currency=currency,
            description=description,
            extra_metadata=metadata,
            status=OrderStatus.CREATED,
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_payment_intent_id(
        self, payment_intent_id: str
    ) -> Order | None:
        result = await self.session.execute(
            select(Order).where(
                Order.stripe_payment_intent_id == payment_intent_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: OrderStatus | None = None,
    ) -> tuple[list[Order], int]:
        query = select(Order).where(Order.user_id == user_id)

        if status:
            query = query.where(Order.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        orders = list(result.scalars().all())

        return orders, total

    async def update_payment_intent(
        self,
        order_id: UUID,
        payment_intent_id: str,
        client_secret: str,
    ) -> Order | None:
        stmt = (
            update(Order)
            .where(Order.id == order_id)
            .values(
                stripe_payment_intent_id=payment_intent_id,
                stripe_client_secret=client_secret,
                status=OrderStatus.PENDING_PAYMENT,
            )
            .returning(Order)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_status(
        self,
        order_id: UUID,
        new_status: OrderStatus,
        paid_at: datetime | None = None,
    ) -> Order | None:
        values = {'status': new_status}
        if paid_at:
            values['paid_at'] = paid_at

        stmt = (
            update(Order)
            .where(Order.id == order_id)
            .values(**values)
            .returning(Order)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_statistics(self) -> dict:
        result = await self.session.execute(
            select(
                func.count(Order.id).label('total_orders'),
                func.count(Order.id).filter(Order.status == OrderStatus.PAID).label('paid_orders'),
                func.count(Order.id).filter(Order.status == OrderStatus.FAILED).label('failed_orders'),
                func.sum(Order.amount).filter(Order.status == OrderStatus.PAID).label('total_revenue'),
            )
        )
        stats = result.one()

        return {
            'total_orders': stats.total_orders or 0,
            'paid_orders': stats.paid_orders or 0,
            'failed_orders': stats.failed_orders or 0,
            'total_revenue': stats.total_revenue or Decimal('0.00'),
        }


class WebhookEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        stripe_event_id: str,
        event_type: str,
        raw_payload: str,
        order_id: UUID | None = None,
    ) -> WebhookEvent:
        event = WebhookEvent(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            raw_payload=raw_payload,
            order_id=order_id,
            processed=False,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def get_by_stripe_event_id(
        self, stripe_event_id: str
    ) -> WebhookEvent | None:
        result = await self.session.execute(
            select(WebhookEvent).where(
                WebhookEvent.stripe_event_id == stripe_event_id
            )
        )
        return result.scalar_one_or_none()

    async def mark_processing(self, event_id: UUID) -> None:
        await self.session.execute(
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(processing_started_at=datetime.now())
        )
        await self.session.commit()

    async def mark_processed(
        self,
        event_id: UUID,
        order_id: UUID | None = None,
        error_message: str | None = None,
    ) -> None:
        values = {
            'processed': error_message is None,
            'processed_at': datetime.now(),
            'error_message': error_message,
        }
        if order_id:
            values['order_id'] = order_id

        await self.session.execute(
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(**values)
        )
        await self.session.commit()

    async def increment_retry_count(self, event_id: UUID) -> None:
        await self.session.execute(
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(retry_count=WebhookEvent.retry_count + 1)
        )
        await self.session.commit()


class PaymentAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_action(
        self,
        order_id: UUID,
        action: str,
        new_status: OrderStatus,
        old_status: OrderStatus | None = None,
        stripe_event_id: str | None = None,
        details: str | None = None,
    ) -> PaymentAudit:
        audit = PaymentAudit(
            order_id=order_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            stripe_event_id=stripe_event_id,
            details=details,
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(audit)
        return audit

    async def get_order_history(self, order_id: UUID) -> list[PaymentAudit]:
        result = await self.session.execute(
            select(PaymentAudit)
            .where(PaymentAudit.order_id == order_id)
            .order_by(PaymentAudit.created_at.asc())
        )
        return list(result.scalars().all())
