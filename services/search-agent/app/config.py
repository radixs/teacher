from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    request_interval_seconds: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    class Config:
        env_prefix = "SEARCH_AGENT_"
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
