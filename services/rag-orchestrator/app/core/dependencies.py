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
def _llm_client_for_url(base_url: str) -> LlmClient:
    return LlmClient(base_url=base_url)


def get_llm_client() -> LlmClient:
    settings = get_settings()
    return _llm_client_for_url(settings.llm_engine_url)


@lru_cache()
def _embedding_client_for_url(base_url: str) -> EmbeddingClient:
    return EmbeddingClient(base_url=base_url)


def get_embedding_client() -> EmbeddingClient:
    settings = get_settings()
    return _embedding_client_for_url(settings.embedding_service_url)


@lru_cache()
def _search_client_for_url(base_url: str) -> SearchClient:
    return SearchClient(base_url=base_url)


def get_search_client() -> SearchClient:
    settings = get_settings()
    return _search_client_for_url(settings.search_agent_url)


@lru_cache()
def _load_grading_config(path: str):
    return load_grading_config(path)


def get_grading_config():
    settings = get_settings()
    config_path = Path(settings.grading_config_path).resolve()
    return _load_grading_config(str(config_path))


@lru_cache()
def _elasticsearch_client_for_url(base_url: str) -> ElasticsearchClient:
    return ElasticsearchClient(base_url=base_url)


def get_elasticsearch_client() -> ElasticsearchClient:
    settings = get_settings()
    return _elasticsearch_client_for_url(settings.elasticsearch_url)


@lru_cache()
def get_exercise_grader():
    settings = get_settings()
    config = get_grading_config()
    profile = config.get(settings.grading_profile)
    return ExerciseGrader(get_llm_client(), profile)


@lru_cache()
def _lab_primer_factory(template_dir: str, output_root: str | None, auto_write: bool) -> LabPrimer:
    template_path = Path(template_dir)
    output_path = Path(output_root) if output_root else None
    return LabPrimer(template_dir=template_path, output_root=output_path, auto_write=auto_write)


def get_lab_primer() -> LabPrimer:
    settings = get_settings()
    template_dir = str(Path(settings.lab_template_dir).resolve())
    output_root = str(Path(settings.lab_output_root).resolve()) if settings.lab_output_root else None
    return _lab_primer_factory(template_dir, output_root, settings.lab_auto_write)
