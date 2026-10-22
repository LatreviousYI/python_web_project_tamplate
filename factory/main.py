from contextlib import asynccontextmanager
from typing import AsyncGenerator

import configs
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


from factory import bootstrap
from factory.middleware import register_error_handlers


def register_routers(app: FastAPI):
    api_router = APIRouter(prefix=f"/{configs.settings.app_name}/api/v1")
    # api_router.include_router(auth.router)
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
    await bootstrap.startup()
    yield
    await bootstrap.shutdown()


app = create_app()
