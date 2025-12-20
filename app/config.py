"""Application configuration using environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or .env file."""

    provider: str = Field(default="google", alias="PROVIDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-1.5-flash", alias="GOOGLE_MODEL")
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        alias="EMBEDDING_MODEL",
    )
    index_path: str = Field(default="app/store/index.faiss", alias="INDEX_PATH")
    meta_path: str = Field(default="app/store/meta.json", alias="META_PATH")
    top_k: int = Field(default=3, alias="TOP_K")
    rerank_k: int = Field(default=3, alias="RERANK_K")
    request_timeout: float = Field(default=30.0, alias="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    redact_placeholder: str = Field(default="[ZREDAKOWANO]")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
