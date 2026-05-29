"""Application configuration."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DSM Operational API"
    app_env: str = "development"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://dsm:dsm_password@localhost:5432/dsm_api"
    admin_token: str = "change-me"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    dsm_release_root: str = "data/dsm/releases"
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    embeddings_enabled: bool = False
    embeddings_required: bool = False
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    openai_api_key: str | None = None
    rag_answer_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    fts_language: str = Field(default="portuguese", pattern="^[a-zA-Z_]+$")
    graph_enabled: bool = True
    graphify_enabled: bool = False
    graphify_cli_path: str | None = None
    graph_export_dir: str = "graph_exports"

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
