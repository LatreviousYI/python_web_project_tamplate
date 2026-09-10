from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import APIRouter, FastAPI

from apps.router import home


def register_routers(app: FastAPI):
    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(home.router)
    app.include_router(api_router)


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
    register_routers(app)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield


app = create_app()
