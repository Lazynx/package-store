import logging

import uvicorn
from dishka import make_async_container
from dishka.integrations import fastapi as fastapi_integration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Settings, settings
from ioc import AppProvider
from presentation import auth

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    container = make_async_container(AppProvider(), context={Settings: settings})
    app = FastAPI(
        title='Auth Service',
        description='Auth Service',
        version='1.0',
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    fastapi_integration.setup_dishka(container, app)

    app.include_router(auth.router)
    return app

if __name__ == '__main__':
    uvicorn.run(create_app(), host='0.0.0.0', port=8000, log_level='debug', reload=True)
