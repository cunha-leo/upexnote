"""UpexNote API entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from . import __version__
from .dependencies import get_reset_service
from .routers import admin_factor, auth_reset, telemetry, tokens
from .service import PasswordResetService


def create_app(initialize_schema: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if initialize_schema:
            get_reset_service().ensure_schema()
        yield

    application = FastAPI(
        title="UpexNote API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @application.get("/health", tags=["operations"])
    def health(service: PasswordResetService = Depends(get_reset_service)):
        try:
            service.health()
        except Exception:
            raise HTTPException(status_code=503, detail="unavailable") from None
        return {"status": "ok", "version": __version__}

    @application.get("/v1", tags=["capabilities"])
    def capabilities():
        return {
            "version": "v1",
            "capabilities": {
                "password_reset": "available",
                "admin_elevation": "reserved",
                "telemetry": "reserved",
                "tokens_webhooks": "reserved",
            },
        }

    application.include_router(auth_reset.router, prefix="/v1")
    application.include_router(admin_factor.router, prefix="/v1")
    application.include_router(telemetry.router, prefix="/v1")
    application.include_router(tokens.router, prefix="/v1")
    return application


app = create_app()
