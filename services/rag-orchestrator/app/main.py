from __future__ import annotations

from fastapi import FastAPI

from .api.routes import sessions_router
from .core.application_bootstrap import ApplicationBootstrap
from .core.config import get_settings

settings = get_settings()
application_bootstrap = ApplicationBootstrap(settings)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=application_bootstrap.lifespan,
)

app.include_router(sessions_router.router, prefix="/v1")


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
