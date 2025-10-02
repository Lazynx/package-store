import json
import logging
from datetime import datetime
from uuid import UUID

import stripe

from config import PackagePricing
from domain.schemas import (
    OrderCreate,
    OrderCreatedEvent,
    OrderFailedEvent,
    OrderPaidEvent,
    OrderResponse,
    PackageInfo,
    PaymentIntentResponse,
)
from infrastructure.broker.events import OrderEventPublisher
from infrastructure.models import OrderStatus, PackageType
from infrastructure.repositories.order import (
    OrderRepository,
    PaymentAuditRepository,
    WebhookEventRepository,
)
from infrastructure.stripe.service import StripeService

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(
        self,
        order_repo: OrderRepository,
        webhook_repo: WebhookEventRepository,
        audit_repo: PaymentAuditRepository,
        stripe_service: StripeService,
        event_publisher: OrderEventPublisher,
        pricing: PackagePricing,
    ):
        self.order_repo = order_repo
        self.webhook_repo = webhook_repo
        self.audit_repo = audit_repo
        self.stripe_service = stripe_service
        self.event_publisher = event_publisher
        self.pricing = pricing

    def get_package_info(self, package_type: PackageType) -> PackageInfo:
        packages = {
            PackageType.BASIC: PackageInfo(
                type=PackageType.BASIC,
                name='Basic Package',
                description='Perfect for small businesses',
                price=self.pricing.basic_price,
                currency='USD',
                features=[
                    '1,000 impressions',
                    'Basic analytics',
                    'Email support',
                ],
            ),
            PackageType.STANDARD: PackageInfo(
                type=PackageType.STANDARD,
                name='Standard Package',
                description='Great for growing companies',
                price=self.pricing.standard_price,
                currency='USD',
                features=[
                    '10,000 impressions',
                    'Advanced analytics',
                    'Priority email support',
                    'A/B testing',
                ],
            ),
            PackageType.PREMIUM: PackageInfo(
                type=PackageType.PREMIUM,
                name='Premium Package',
                description='For established brands',
                price=self.pricing.premium_price,
                currency='USD',
                features=[
                    '100,000 impressions',
                    'Full analytics suite',
                    '24/7 phone support',
                    'A/B testing',
                    'Custom targeting',
                ],
            ),
        }
        return packages[package_type]

    def get_all_packages(self) -> list[PackageInfo]:
        return [
            self.get_package_info(PackageType.BASIC),
            self.get_package_info(PackageType.STANDARD),
            self.get_package_info(PackageType.PREMIUM),
        ]

    async def create_order(
        self,
        user_id: UUID,
        order_data: OrderCreate,
    ) -> tuple[OrderResponse, PaymentIntentResponse]:
        package_info = self.get_package_info(order_data.package_type)

        order = await self.order_repo.create(
            user_id=user_id,
            package_type=order_data.package_type,
            amount=package_info.price,
            currency=package_info.currency,
            description=package_info.name,
            metadata=json.dumps(order_data.metadata) if order_data.metadata else None,
        )

        await self.audit_repo.log_action(
            order_id=order.id,
            action='order_created',
            new_status=OrderStatus.CREATED,
            details=f'Package: {order_data.package_type}',
        )

        try:
            payment_intent_id, client_secret = await self.stripe_service.create_payment_intent(
                order_id=order.id,
                amount=order.amount,
                currency=order.currency,
                metadata={'package_type': order_data.package_type},
            )

            order = await self.order_repo.update_payment_intent(
                order_id=order.id,
                payment_intent_id=payment_intent_id,
                client_secret=client_secret,
            )

            await self.audit_repo.log_action(
                order_id=order.id,
                action='payment_intent_created',
                old_status=OrderStatus.CREATED,
                new_status=OrderStatus.PENDING_PAYMENT,
                details=f'Payment Intent ID: {payment_intent_id}',
            )

        except Exception as e:
            logger.error(f'Failed to create payment intent for order {order.id}: {e}')
            raise

        await self.event_publisher.publish_order_created(
            OrderCreatedEvent(
                order_id=order.id,
                user_id=order.user_id,
                package_type=order.package_type,
                amount=order.amount,
                currency=order.currency,
                created_at=order.created_at,
            )
        )

        return (
            OrderResponse.model_validate(order),
            PaymentIntentResponse(
                order_id=order.id,
                client_secret=client_secret,
                amount=order.amount,
                currency=order.currency,
                status=order.status,
            ),
        )

    async def get_order(self, order_id: UUID, user_id: UUID) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)

        if not order:
            raise ValueError('Order not found')

        if order.user_id != user_id:
            raise ValueError('Access denied')

        return OrderResponse.model_validate(order)

    async def get_user_orders(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: OrderStatus | None = None,
    ) -> tuple[list[OrderResponse], int]:
        offset = (page - 1) * page_size
        orders, total = await self.order_repo.get_user_orders(
            user_id=user_id,
            limit=page_size,
            offset=offset,
            status=status,
        )

        order_responses = [OrderResponse.model_validate(order) for order in orders]
        return order_responses, total

    async def cancel_order(self, order_id: UUID, user_id: UUID) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)

        if not order:
            raise ValueError('Order not found')

        if order.user_id != user_id:
            raise ValueError('Access denied')

        if order.status not in [OrderStatus.CREATED, OrderStatus.PENDING_PAYMENT]:
            raise ValueError(f'Cannot cancel order with status {order.status}')

        if order.stripe_payment_intent_id:
            try:
                await self.stripe_service.cancel_payment_intent(
                    order.stripe_payment_intent_id
                )
            except Exception as e:
                logger.error(f'Failed to cancel payment intent: {e}')

        old_status = order.status
        order = await self.order_repo.update_status(
            order_id=order.id,
            new_status=OrderStatus.CANCELLED,
        )

        await self.audit_repo.log_action(
            order_id=order.id,
            action='order_cancelled',
            old_status=old_status,
            new_status=OrderStatus.CANCELLED,
        )

        return OrderResponse.model_validate(order)

    async def process_webhook(
        self,
        stripe_event: stripe.Event,
        raw_payload: str,
    ) -> None:
        event_id = stripe_event.id
        event_type = stripe_event.type

        logger.info(f'Processing webhook event: {event_type} (ID: {event_id})')

        existing_event = await self.webhook_repo.get_by_stripe_event_id(event_id)
        if existing_event:
            if existing_event.processed:
                logger.info(f'Event {event_id} already processed, skipping')
                return
            else:
                logger.info(f'Event {event_id} is being reprocessed')
                await self.webhook_repo.increment_retry_count(existing_event.id)
        else:
            order_id = self.stripe_service.extract_order_id_from_event(stripe_event)
            existing_event = await self.webhook_repo.create(
                stripe_event_id=event_id,
                event_type=event_type,
                raw_payload=raw_payload,
                order_id=order_id,
            )

        await self.webhook_repo.mark_processing(existing_event.id)

        try:
            if event_type == 'payment_intent.succeeded':
                await self._handle_payment_succeeded(stripe_event, existing_event.id)
            elif event_type == 'payment_intent.payment_failed':
                await self._handle_payment_failed(stripe_event, existing_event.id)
            elif event_type == 'payment_intent.canceled':
                await self._handle_payment_canceled(stripe_event, existing_event.id)
            else:
                logger.info(f'Unhandled event type: {event_type}')

            await self.webhook_repo.mark_processed(existing_event.id)

        except Exception as e:
            error_msg = f'Error processing webhook: {str(e)}'
            logger.error(error_msg)
            await self.webhook_repo.mark_processed(
                existing_event.id,
                error_message=error_msg,
            )
            raise

    async def _handle_payment_succeeded(
        self,
        event: stripe.Event,
        webhook_event_id: UUID,
    ) -> None:
        payment_intent = event.data.object
        payment_intent_id = payment_intent.id

        order = await self.order_repo.get_by_payment_intent_id(payment_intent_id)
        if not order:
            logger.error(f'Order not found for payment intent {payment_intent_id}')
            return

        await self.webhook_repo.mark_processed(webhook_event_id, order_id=order.id)

        if order.status == OrderStatus.PAID:
            logger.info(f'Order {order.id} already paid, skipping')
            return

        old_status = order.status
        paid_at = datetime.now()
        order = await self.order_repo.update_status(
            order_id=order.id,
            new_status=OrderStatus.PAID,
            paid_at=paid_at,
        )

        await self.audit_repo.log_action(
            order_id=order.id,
            action='payment_succeeded',
            old_status=old_status,
            new_status=OrderStatus.PAID,
            stripe_event_id=event.id,
            details=f'Payment Intent: {payment_intent_id}',
        )

        await self.event_publisher.publish_order_paid(
            OrderPaidEvent(
                order_id=order.id,
                user_id=order.user_id,
                package_type=order.package_type,
                amount=order.amount,
                currency=order.currency,
                paid_at=paid_at,
                stripe_payment_intent_id=payment_intent_id,
            )
        )

        logger.info(f'Order {order.id} marked as paid')

    async def _handle_payment_failed(
        self,
        event: stripe.Event,
        webhook_event_id: UUID,
    ) -> None:
        payment_intent = event.data.object
        payment_intent_id = payment_intent.id

        order = await self.order_repo.get_by_payment_intent_id(payment_intent_id)
        if not order:
            logger.error(f'Order not found for payment intent {payment_intent_id}')
            return

        await self.webhook_repo.mark_processed(webhook_event_id, order_id=order.id)

        old_status = order.status
        order = await self.order_repo.update_status(
            order_id=order.id,
            new_status=OrderStatus.FAILED,
        )

        error_message = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
        await self.audit_repo.log_action(
            order_id=order.id,
            action='payment_failed',
            old_status=old_status,
            new_status=OrderStatus.FAILED,
            stripe_event_id=event.id,
            details=f'Error: {error_message}',
        )

        await self.event_publisher.publish_order_failed(
            OrderFailedEvent(
                order_id=order.id,
                user_id=order.user_id,
                reason=error_message,
                failed_at=datetime.now(),
            )
        )

        logger.info(f'Order {order.id} marked as failed')

    async def _handle_payment_canceled(
        self,
        event: stripe.Event,
        webhook_event_id: UUID,
    ) -> None:
        payment_intent = event.data.object
        payment_intent_id = payment_intent.id

        order = await self.order_repo.get_by_payment_intent_id(payment_intent_id)
        if not order:
            return

        await self.webhook_repo.mark_processed(webhook_event_id, order_id=order.id)

        old_status = order.status
        order = await self.order_repo.update_status(
            order_id=order.id,
            new_status=OrderStatus.CANCELLED,
        )

        await self.audit_repo.log_action(
            order_id=order.id,
            action='payment_canceled',
            old_status=old_status,
            new_status=OrderStatus.CANCELLED,
            stripe_event_id=event.id,
        )

        logger.info(f'Order {order.id} marked as cancelled')
