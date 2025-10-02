import logging

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from domain.schemas import OrderCreatedEvent, OrderFailedEvent, OrderPaidEvent

logger = logging.getLogger(__name__)

orders_exchange = RabbitExchange(
    name='orders',
    type=ExchangeType.TOPIC,
    durable=True,
)

order_created_queue = RabbitQueue(
    name='order.created',
    durable=True,
    routing_key='order.created',
)

order_paid_queue = RabbitQueue(
    name='order.paid',
    durable=True,
    routing_key='order.paid',
)

order_failed_queue = RabbitQueue(
    name='order.failed',
    durable=True,
    routing_key='order.failed',
)


class OrderEventPublisher:
    def __init__(self, broker: RabbitBroker):
        self.broker = broker

    async def publish_order_created(self, event: OrderCreatedEvent) -> None:
        try:
            await self.broker.publish(
                message=event.model_dump(mode='json'),
                exchange=orders_exchange,
                routing_key='order.created',
            )
            print(f'Published order.created event for order {event.order_id}')
        except Exception as e:
            logger.error(f'Failed to publish order.created event: {e}')
            raise

    async def publish_order_paid(self, event: OrderPaidEvent) -> None:
        try:
            await self.broker.publish(
                message=event.model_dump(mode='json'),
                exchange=orders_exchange,
                routing_key='order.paid',
            )
            logger.info(f'Published order.paid event for order {event.order_id}')
        except Exception as e:
            logger.error(f'Failed to publish order.paid event: {e}')
            raise

    async def publish_order_failed(self, event: OrderFailedEvent) -> None:
        try:
            await self.broker.publish(
                message=event.model_dump(mode='json'),
                exchange=orders_exchange,
                routing_key='order.failed',
            )
            logger.info(f'Published order.failed event for order {event.order_id}')
        except Exception as e:
            logger.error(f'Failed to publish order.failed event: {e}')
            raise
