from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Callable, TypeVar

import httpx
from fastapi import FastAPI

from .application_bootstrap_error import ApplicationBootstrapError
from .config import Settings
from .flow_logger import log_flow
from .service_container import (
    get_elasticsearch_client,
    get_embedding_client,
    get_exercise_grader_service,
    get_lab_primer_service,
    get_llm_client,
    get_search_client,
    get_session_manager_service,
    get_session_repository,
)

DependencyType = TypeVar("DependencyType")


class ApplicationBootstrap:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        await self.startup(app)
        try:
            yield
        finally:
            await self.shutdown()

    async def startup(self, app: FastAPI) -> None:
        session_manager_service = self._resolve_dependency(app, get_session_manager_service)
        session_repository = self._resolve_dependency(app, get_session_repository)
        _ = self._resolve_dependency(app, get_llm_client)
        _ = self._resolve_dependency(app, get_embedding_client)
        _ = self._resolve_dependency(app, get_search_client)
        _ = self._resolve_dependency(app, get_elasticsearch_client)
        _ = self._resolve_dependency(app, get_exercise_grader_service)
        _ = self._resolve_dependency(app, get_lab_primer_service)

        log_flow(
            "rag-orchestrator",
            "startup.started",
            "RAG orchestrator startup began and dependency clients were initialized.",
        )

        stored_sessions = []
        max_attempts = 15
        wait_seconds = 2
        retryable_status_codes = {429, 502, 503}

        for attempt in range(1, max_attempts + 1):
            try:
                stored_sessions = await session_repository.list()
                break
            except httpx.RequestError as exc:
                if attempt == max_attempts:
                    log_flow(
                        "rag-orchestrator",
                        "startup.failed",
                        "RAG orchestrator could not reach Elasticsearch during startup and will stop the process.",
                        attempts=attempt,
                        error=str(exc),
                    )
                    raise ApplicationBootstrapError(
                        "Startup failed because Elasticsearch could not be reached."
                    ) from exc

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
                            "startup.failed",
                            "RAG orchestrator could reach Elasticsearch, but the cluster never became query-ready during startup.",
                            attempts=attempt,
                            status_code=exc.response.status_code,
                        )
                        raise ApplicationBootstrapError(
                            "Startup failed because Elasticsearch never became query-ready."
                        ) from exc

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
                    log_flow(
                        "rag-orchestrator",
                        "startup.failed",
                        "RAG orchestrator started before the sessions index existed and will stop until bootstrap is run.",
                        sessions_index=self._settings.index_sessions,
                        status_code=exc.response.status_code,
                    )
                    raise ApplicationBootstrapError(
                        "Startup failed because the sessions index does not exist yet."
                    ) from exc
                raise

        for stored_session in stored_sessions:
            session_manager_service.load_session(stored_session)

        log_flow(
            "rag-orchestrator",
            "startup.completed",
            "RAG orchestrator started and preloaded persisted sessions from Elasticsearch.",
            restored_sessions=len(stored_sessions),
        )

    async def shutdown(self) -> None:
        log_flow(
            "rag-orchestrator",
            "shutdown.started",
            "RAG orchestrator is shutting down and closing downstream HTTP clients.",
        )
        await get_llm_client().close()
        await get_embedding_client().close()
        await get_search_client().close()
        await get_elasticsearch_client().close()

    @staticmethod
    def _resolve_dependency(
        app: FastAPI,
        dependency_factory: Callable[[], DependencyType],
    ) -> DependencyType:
        dependency_override = app.dependency_overrides.get(dependency_factory)
        return dependency_override() if dependency_override else dependency_factory()
