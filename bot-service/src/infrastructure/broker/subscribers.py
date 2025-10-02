from dishka import FromDishka
from dishka.integrations.faststream import inject
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from application.event_handler import OrderEventHandler
from domain.schemas import OrderCreatedEvent, OrderFailedEvent, OrderPaidEvent

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


def register_subscribers(broker: RabbitBroker) -> None:
    @broker.subscriber(queue=order_created_queue, exchange=orders_exchange)
    @inject
    async def on_order_created(
        event: OrderCreatedEvent,
        handler: FromDishka[OrderEventHandler]
    ) -> None:
        await handler.handle_created(event)

    @broker.subscriber(queue=order_paid_queue, exchange=orders_exchange)
    @inject
    async def on_order_paid(
        event: OrderPaidEvent,
        handler: FromDishka[OrderEventHandler]
    ) -> None:
        await handler.handle_paid(event)

    @broker.subscriber(queue=order_failed_queue, exchange=orders_exchange)
    @inject
    async def on_order_failed(
        event: OrderFailedEvent,
        handler: FromDishka[OrderEventHandler]
    ) -> None:
        await handler.handle_failed(event)
