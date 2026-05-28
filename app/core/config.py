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
    embeddings_enabled: bool = False
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    openai_api_key: str | None = None
    rag_answer_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    fts_language: str = Field(default="portuguese", pattern="^[a-zA-Z_]+$")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
