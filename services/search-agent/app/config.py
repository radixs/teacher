from pydantic import BaseSettings


class Settings(BaseSettings):
    request_interval_seconds: float = 2.0
    user_agent: str = "teacher-app-bot/0.1"

    class Config:
        env_prefix = "SEARCH_AGENT_"
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
