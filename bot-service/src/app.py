import asyncio
import logging

from dishka import make_async_container
from dishka.integrations.faststream import setup_dishka
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from config import Settings, settings
from infrastructure.broker.subscribers import register_subscribers
from infrastructure.resources.broker import new_broker
from infrastructure.broker.subscribers import orders_exchange
from ioc import AppProvider

logger = logging.getLogger(__name__)

broker = new_broker(settings.rabbitmq)
amqp = FastStream(broker=broker)

container = make_async_container(AppProvider(), context={Settings: settings, RabbitBroker: broker})
setup_dishka(container, app=amqp)

register_subscribers(broker)

async def main():
    await broker.start()
    await broker.declare_exchange(orders_exchange)
    await amqp.run()
    await broker.stop()

if __name__ == '__main__':
    asyncio.run(main())
