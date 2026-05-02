from __future__ import annotations

from fastapi import FastAPI

from .api.routes import sessions
from .core.config import get_settings
from .core.dependencies import (
    get_embedding_client,
    get_llm_client,
    get_search_client,
    get_elasticsearch_client,
    get_exercise_grader,
    get_lab_primer,
    get_session_manager,
    get_session_store,
)

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(sessions.router, prefix="/v1")


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event() -> None:
    # Touch dependencies so they're ready to use and to surface misconfiguration early.
    session_manager_override = app.dependency_overrides.get(get_session_manager)
    session_store_override = app.dependency_overrides.get(get_session_store)

    session_manager = session_manager_override() if session_manager_override else get_session_manager()
    session_store = session_store_override() if session_store_override else get_session_store()
    _ = get_llm_client()
    _ = get_embedding_client()
    _ = get_search_client()
    _ = get_elasticsearch_client()
    _ = get_exercise_grader()
    _ = get_lab_primer()

    stored_sessions = await session_store.list()
    for session in stored_sessions:
        session_manager.register_session(session)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await get_llm_client().close()
    await get_embedding_client().close()
    await get_search_client().close()
    await get_elasticsearch_client().close()
    # Exercise grader reuses LLM client; nothing additional to close.
