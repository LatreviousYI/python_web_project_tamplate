from contextlib import asynccontextmanager
from typing import AsyncGenerator

import configs
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.router import health
from factory import bootstrap
from factory.middleware import register_error_handlers


def register_routers(app: FastAPI):
    api_router = APIRouter(prefix=f"/{configs.settings.app_name}/api/v1")
    api_router.include_router(health.router)
    # api_router.include_router(auth.router)
    app.include_router(api_router)


def create_app() -> FastAPI:
    docs_enabled = configs.settings.env in ("dev", "test")
    app = FastAPI(
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=configs.settings.cors_allow_origins,
        allow_credentials=configs.settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    register_routers(app)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        await bootstrap.startup()
        yield
    finally:
        await bootstrap.shutdown()


app = create_app()
