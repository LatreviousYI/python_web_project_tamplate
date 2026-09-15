from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.router import auth, common, home, post, project_center, reply
from apps.service.lock import cleanup_expired_locks
from apps.tasks import start_scheduler
from factory.middleware import register_error_handlers
from factory.sync_db import sync_db
from utils import httpx_utils


def register_routers(app: FastAPI):
    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(home.router)
    api_router.include_router(auth.router)
    api_router.include_router(post.router)
    api_router.include_router(reply.router)
    api_router.include_router(common.router)
    api_router.include_router(project_center.router)
    app.include_router(api_router)


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    register_routers(app)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await sync_db()
    await cleanup_expired_locks()
    scheduler = start_scheduler()
    yield

    scheduler.shutdown()
    await httpx_utils.close_httpx()


app = create_app()
