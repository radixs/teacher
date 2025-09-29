from functools import lru_cache
from pathlib import Path

from .config import Settings, get_settings
from ..services.session_manager import SessionManager
from ..clients.llm import LlmClient
from ..clients.embedding import EmbeddingClient
from ..clients.search import SearchClient
from ..clients.elasticsearch import ElasticsearchClient
from ..services.grading import ExerciseGrader, load_grading_config
from ..services.lab_primer import LabPrimer


@lru_cache()
def get_session_manager() -> SessionManager:
    return SessionManager()


@lru_cache()
def get_llm_client(settings: Settings | None = None) -> LlmClient:
    settings = settings or get_settings()
    return LlmClient(base_url=settings.llm_engine_url)


@lru_cache()
def get_embedding_client(settings: Settings | None = None) -> EmbeddingClient:
    settings = settings or get_settings()
    return EmbeddingClient(base_url=settings.embedding_service_url)


@lru_cache()
def get_search_client(settings: Settings | None = None) -> SearchClient:
    settings = settings or get_settings()
    return SearchClient(base_url=settings.search_agent_url)


@lru_cache()
def get_grading_config(settings: Settings | None = None):
    settings = settings or get_settings()
    return load_grading_config(settings.grading_config_path)


@lru_cache()
def get_elasticsearch_client(settings: Settings | None = None) -> ElasticsearchClient:
    settings = settings or get_settings()
    return ElasticsearchClient(base_url=settings.elasticsearch_url)


@lru_cache()
def get_exercise_grader(settings: Settings | None = None):
    settings = settings or get_settings()
    config = get_grading_config(settings)
    profile = config.get(settings.grading_profile)
    return ExerciseGrader(get_llm_client(settings), profile)


@lru_cache()
def get_lab_primer(settings: Settings | None = None) -> LabPrimer:
    settings = settings or get_settings()
    template_dir = Path(settings.lab_template_dir).resolve()
    output_root = Path(settings.lab_output_root).resolve() if settings.lab_output_root else None
    return LabPrimer(template_dir=template_dir, output_root=output_root, auto_write=settings.lab_auto_write)
