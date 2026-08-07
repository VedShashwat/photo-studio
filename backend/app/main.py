from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.api.routes.images import router as images_router
from app.api.routes.generation_jobs import router as generation_jobs_router
from app.api.routes.downloads import router as downloads_router
from app.api.routes.history import prompt_router as prompt_history_router
from app.api.routes.history import router as history_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Product Photography Studio API", version=settings.app_version, lifespan=lifespan)
    install_exception_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(images_router, prefix="/api")
    app.include_router(generation_jobs_router, prefix="/api")
    app.include_router(downloads_router, prefix="/api")
    app.include_router(history_router, prefix="/api")
    app.include_router(prompt_history_router, prefix="/api")
    return app


app = create_app()
