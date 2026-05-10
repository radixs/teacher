from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI

from .api.routes import sessions
from .core.config import get_settings
from .core.flow_logger import log_flow
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

    log_flow(
        "rag-orchestrator",
        "startup.started",
        "RAG orchestrator startup began and dependency clients were initialized.",
    )

    stored_sessions = []
    bootstrap_pending = False
    max_attempts = 15
    wait_seconds = 2

    retryable_status_codes = {429, 502, 503}

    for attempt in range(1, max_attempts + 1):
        try:
            stored_sessions = await session_store.list()
            break
        except httpx.RequestError as exc:
            if attempt == max_attempts:
                log_flow(
                    "rag-orchestrator",
                    "startup.degraded",
                    "RAG orchestrator could not reach Elasticsearch during startup and will continue without restored sessions.",
                    attempts=attempt,
                    error=str(exc),
                )
                break

            log_flow(
                "rag-orchestrator",
                "startup.waiting_for_elasticsearch",
                "RAG orchestrator is waiting for Elasticsearch to accept connections before restoring sessions.",
                attempt=attempt,
                max_attempts=max_attempts,
                wait_seconds=wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in retryable_status_codes:
                if attempt == max_attempts:
                    log_flow(
                        "rag-orchestrator",
                        "startup.degraded",
                        "RAG orchestrator could reach Elasticsearch, but the cluster never became query-ready during startup. Continuing without restored sessions.",
                        attempts=attempt,
                        status_code=exc.response.status_code,
                    )
                    break

                log_flow(
                    "rag-orchestrator",
                    "startup.waiting_for_elasticsearch",
                    "RAG orchestrator reached Elasticsearch, but the cluster is still warming up before session queries can run.",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    status_code=exc.response.status_code,
                    wait_seconds=wait_seconds,
                )
                await asyncio.sleep(wait_seconds)
                continue

            if exc.response.status_code == 404:
                bootstrap_pending = True
                log_flow(
                    "rag-orchestrator",
                    "startup.bootstrap_pending",
                    "RAG orchestrator started before the sessions index existed and will continue with an empty in-memory session registry until bootstrap is run.",
                    sessions_index=settings.index_sessions,
                    status_code=exc.response.status_code,
                )
                break
            raise

    for session in stored_sessions:
        session_manager.register_session(session)

    log_flow(
        "rag-orchestrator",
        "startup.completed",
        "RAG orchestrator started and preloaded persisted sessions from Elasticsearch.",
        bootstrap_pending=bootstrap_pending,
        restored_sessions=len(stored_sessions),
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    log_flow(
        "rag-orchestrator",
        "shutdown.started",
        "RAG orchestrator is shutting down and closing downstream HTTP clients.",
    )
    await get_llm_client().close()
    await get_embedding_client().close()
    await get_search_client().close()
    await get_elasticsearch_client().close()
    # Exercise grader reuses LLM client; nothing additional to close.
