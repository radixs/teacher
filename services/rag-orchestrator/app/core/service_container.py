from __future__ import annotations

"""Dependency factory functions used by FastAPI.

This module plays a role similar to a Laravel service container registration
file. Each function creates or retrieves one dependency that can be injected
into route handlers or higher-level services.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from .config import Settings, get_settings, load_grading_config
from ..clients.elasticsearch_client import ElasticsearchClient
from ..clients.embedding_client import EmbeddingClient
from ..clients.llm_client import LlmClient
from ..clients.search_client import SearchClient
from ..repositories.learning_memory_repository import LearningMemoryRepository
from ..repositories.session_repository import SessionRepository
from ..services.calibration_workflow_service import CalibrationWorkflowService
from ..services.exercise_grader_service import ExerciseGraderService
from ..services.lab_primer_service import LabPrimerService
from ..services.learning_workflow_service import LearningWorkflowService
from ..services.resource_discovery_service import ResourceDiscoveryService
from ..services.session_manager_service import SessionManagerService
from ..services.tuning_workflow_service import TuningWorkflowService
from ..services.user_workflow_service import UserWorkflowService


@lru_cache()
def get_session_manager_service() -> SessionManagerService:
    """Return the shared in-memory session manager used across requests."""
    return SessionManagerService()


@lru_cache()
def get_session_repository() -> SessionRepository:
    """Build the persistence gateway for top-level session documents."""
    settings = get_settings()
    elasticsearch_client = get_elasticsearch_client()
    indices = settings.indices
    return SessionRepository(elasticsearch_client, indices["sessions"])


def get_learning_memory_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    elasticsearch_client: Annotated[ElasticsearchClient, Depends(get_elasticsearch_client)],
) -> LearningMemoryRepository:
    """Build the repository that owns learning-flow Elasticsearch writes."""
    return LearningMemoryRepository(elasticsearch_client, settings.indices)


def get_resource_discovery_service(
    search_client: Annotated[SearchClient, Depends(get_search_client)],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    learning_memory_repository: Annotated[
        LearningMemoryRepository,
        Depends(get_learning_memory_repository),
    ],
) -> ResourceDiscoveryService:
    """Compose the service that coordinates search-agent calls and resource persistence."""
    return ResourceDiscoveryService(
        search_client=search_client,
        embedding_client=embedding_client,
        learning_memory_repository=learning_memory_repository,
    )


@lru_cache()
def _llm_client_for_url(base_url: str) -> LlmClient:
    """Cache one LLM client per configured base URL."""
    return LlmClient(base_url=base_url)


def get_llm_client() -> LlmClient:
    """Resolve the LLM client for the current application settings."""
    settings = get_settings()
    return _llm_client_for_url(settings.llm_engine_url)


@lru_cache()
def _embedding_client_for_url(base_url: str) -> EmbeddingClient:
    """Cache one embedding client per configured base URL."""
    return EmbeddingClient(base_url=base_url)


def get_embedding_client() -> EmbeddingClient:
    """Resolve the embedding client for the current application settings."""
    settings = get_settings()
    return _embedding_client_for_url(settings.embedding_service_url)


@lru_cache()
def _search_client_for_url(base_url: str) -> SearchClient:
    """Cache one search client per configured base URL."""
    return SearchClient(base_url=base_url)


def get_search_client() -> SearchClient:
    """Resolve the external search client for the current application settings."""
    settings = get_settings()
    return _search_client_for_url(settings.search_agent_url)


@lru_cache()
def _load_grading_config(path: str):
    """Cache the parsed grading configuration file by absolute path."""
    return load_grading_config(path)


def get_grading_config():
    """Load the configured grading profiles from disk."""
    settings = get_settings()
    config_path = Path(settings.grading_config_path).resolve()
    return _load_grading_config(str(config_path))


@lru_cache()
def _elasticsearch_client_for_url(base_url: str) -> ElasticsearchClient:
    """Cache one Elasticsearch client per configured base URL."""
    return ElasticsearchClient(base_url=base_url)


def get_elasticsearch_client() -> ElasticsearchClient:
    """Resolve the Elasticsearch client for the current application settings."""
    settings = get_settings()
    return _elasticsearch_client_for_url(settings.elasticsearch_url)


@lru_cache()
def get_exercise_grader_service() -> ExerciseGraderService:
    """Build the grader with the active rubric profile and LLM client."""
    settings = get_settings()
    grading_config = get_grading_config()
    grading_profile = grading_config.get(settings.grading_profile)
    return ExerciseGraderService(get_llm_client(), grading_profile)


def get_tuning_workflow_service(
    session_manager_service: Annotated[
        SessionManagerService,
        Depends(get_session_manager_service),
    ],
    learning_memory_repository: Annotated[
        LearningMemoryRepository,
        Depends(get_learning_memory_repository),
    ],
    resource_discovery_service: Annotated[
        ResourceDiscoveryService,
        Depends(get_resource_discovery_service),
    ],
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
) -> TuningWorkflowService:
    """Compose the service that bridges calibration completion into learning."""
    return TuningWorkflowService(
        session_manager_service=session_manager_service,
        learning_memory_repository=learning_memory_repository,
        resource_discovery_service=resource_discovery_service,
        llm_client=llm_client,
    )


def get_calibration_workflow_service(
    session_manager_service: Annotated[
        SessionManagerService,
        Depends(get_session_manager_service),
    ],
    learning_memory_repository: Annotated[
        LearningMemoryRepository,
        Depends(get_learning_memory_repository),
    ],
    tuning_workflow_service: Annotated[
        TuningWorkflowService,
        Depends(get_tuning_workflow_service),
    ],
) -> CalibrationWorkflowService:
    """Compose the service that owns calibration answer processing."""
    return CalibrationWorkflowService(
        session_manager_service=session_manager_service,
        learning_memory_repository=learning_memory_repository,
        tuning_workflow_service=tuning_workflow_service,
    )


def get_learning_workflow_service(
    session_manager_service: Annotated[
        SessionManagerService,
        Depends(get_session_manager_service),
    ],
    learning_memory_repository: Annotated[
        LearningMemoryRepository,
        Depends(get_learning_memory_repository),
    ],
    exercise_grader_service: Annotated[
        ExerciseGraderService,
        Depends(get_exercise_grader_service),
    ],
) -> LearningWorkflowService:
    """Compose the service that owns active learning answer evaluation."""
    return LearningWorkflowService(
        session_manager_service=session_manager_service,
        learning_memory_repository=learning_memory_repository,
        exercise_grader_service=exercise_grader_service,
    )


@lru_cache()
def _lab_primer_factory(
    template_dir: str,
    output_root: str | None,
    auto_write: bool,
) -> LabPrimerService:
    """Cache the lab primer service for a specific template/output configuration."""
    template_path = Path(template_dir)
    output_path = Path(output_root) if output_root else None
    return LabPrimerService(
        template_dir=template_path,
        output_root=output_path,
        auto_write=auto_write,
    )


def get_lab_primer_service() -> LabPrimerService:
    """Resolve the lab primer service using the configured template paths."""
    settings = get_settings()
    template_dir = str(Path(settings.lab_template_dir).resolve())
    output_root = str(Path(settings.lab_output_root).resolve()) if settings.lab_output_root else None
    return _lab_primer_factory(template_dir, output_root, settings.lab_auto_write)


def get_user_workflow_service(
    session_manager_service: Annotated[
        SessionManagerService,
        Depends(get_session_manager_service),
    ],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    learning_memory_repository: Annotated[
        LearningMemoryRepository,
        Depends(get_learning_memory_repository),
    ],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
    calibration_workflow_service: Annotated[
        CalibrationWorkflowService,
        Depends(get_calibration_workflow_service),
    ],
    learning_workflow_service: Annotated[
        LearningWorkflowService,
        Depends(get_learning_workflow_service),
    ],
    lab_primer_service: Annotated[LabPrimerService, Depends(get_lab_primer_service)],
) -> UserWorkflowService:
    """Compose the main session use-case service from its lower-level parts."""
    return UserWorkflowService(
        session_manager_service=session_manager_service,
        session_repository=session_repository,
        learning_memory_repository=learning_memory_repository,
        embedding_client=embedding_client,
        llm_client=llm_client,
        calibration_workflow_service=calibration_workflow_service,
        learning_workflow_service=learning_workflow_service,
        lab_primer_service=lab_primer_service,
    )
