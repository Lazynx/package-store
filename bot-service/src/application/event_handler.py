import logging

from domain.schemas import OrderCreatedEvent, OrderFailedEvent, OrderPaidEvent
from infrastructure.telegram import TelegramNotifier

logger = logging.getLogger(__name__)

class OrderEventHandler:
    def __init__(self, notifier: TelegramNotifier):
        self.notifier = notifier

    async def handle_created(self, event: OrderCreatedEvent) -> None:
        try:
            text = (
                f'🟢 Order Created\n'
                f'User: {event.user_id}\n'
                f'Order ID: {event.order_id}\n'
                f'Package: {event.package_type}\n'
                f'Amount: {event.amount} {event.currency}\n'
                f'Created At: {event.created_at}'
            )
            await self.notifier.send_message(text)
            logger.info(f'Sent notification for order created: {event.order_id}')
        except Exception as e:
            logger.error(f'Failed to handle order.created event: {e}')

    async def handle_paid(self, event: OrderPaidEvent) -> None:
        try:
            text = (
                f'💰 Order Paid\n'
                f'User: {event.user_id}\n'
                f'Order ID: {event.order_id}\n'
                f'Package: {event.package_type}\n'
                f'Amount: {event.amount} {event.currency}\n'
                f'Paid At: {event.paid_at}\n'
                f'Stripe ID: {event.stripe_payment_intent_id}'
            )
            await self.notifier.send_message(text)
            logger.info(f'Sent notification for order paid: {event.order_id}')
        except Exception as e:
            logger.error(f'Failed to handle order.paid event: {e}')

    async def handle_failed(self, event: OrderFailedEvent) -> None:
        try:
            text = (
                f'❌ Order Failed\n'
                f'User: {event.user_id}\n'
                f'Order ID: {event.order_id}\n'
                f'Reason: {event.reason}\n'
                f'Failed At: {event.failed_at}'
            )
            await self.notifier.send_message(text)
            logger.info(f'Sent notification for order failed: {event.order_id}')
        except Exception as e:
            logger.error(f'Failed to handle order.failed event: {e}')
