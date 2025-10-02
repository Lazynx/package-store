import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from dishka import make_async_container
from dishka.integrations import fastapi as fastapi_integration, faststream as faststream_integration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from config import Settings, settings
from infrastructure.broker.events import orders_exchange
from infrastructure.resources.broker import new_broker
from ioc import AppProvider
from presentation.billing import router as billing_router

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    broker = new_broker(settings.rabbitmq)
    container = make_async_container(
        AppProvider(),
        context={
            Settings: settings,
            RabbitBroker: broker,
        }
    )
    amqp = FastStream(broker=broker)
    faststream_integration.setup_dishka(container, app=amqp)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await broker.start()
        await broker.declare_exchange(orders_exchange)
        yield
        await broker.stop()

    http = FastAPI(
        title='Billing Service',
        description='Billing Service',
        version='1.0',
        lifespan=lifespan,
    )
    http.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    fastapi_integration.setup_dishka(container, http)

    http.include_router(billing_router)
    return http

if __name__ == '__main__':
    uvicorn.run(create_app(), host='0.0.0.0', port=8000, log_level='debug', reload=True)
