from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "RAG Orchestrator"
    host: str = "0.0.0.0"
    port: int = 9000
    reload: bool = False

    llm_engine_url: str = "http://llm-engine:8000"
    embedding_service_url: str = "http://embedding-worker:9100"
    search_agent_url: str = "http://search-agent:9205"
    elasticsearch_url: str = "http://elasticsearch:9200"

    index_user_profiles: str = "user_profiles"
    index_knowledge_snapshots: str = "knowledge_snapshots"
    index_learning_resources: str = "learning_resources"
    index_dependency_graph: str = "dependency_graph"
    index_session_interactions: str = "session_interactions"
    index_sessions: str = "sessions"

    grading_profile: str = "default"
    grading_config_path: str = "config/grading_profiles.yaml"

    lab_template_dir: str = "lab_templates"
    lab_output_root: str | None = None
    lab_auto_write: bool = False

    @property
    def indices(self) -> dict[str, str]:
        return {
            'user_profiles': self.index_user_profiles,
            'knowledge_snapshots': self.index_knowledge_snapshots,
            'learning_resources': self.index_learning_resources,
            'dependency_graph': self.index_dependency_graph,
            'session_interactions': self.index_session_interactions,
            'sessions': self.index_sessions,
        }

    class Config:
        env_prefix = "RAG_"
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()
