"""Configuration management for Chronicle."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "Chronicle"
    app_version: str = "0.2.0"
    environment: Literal["development", "production", "testing"] = "production"
    debug: bool = False

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_reload: bool = False

    # Database
    db_path: str = "data/chronicle.db"

    # Collector
    collector_interval: int = 60  # seconds between HN fetches
    collector_story_limit: int = 60  # number of stories to fetch
    collector_timeout: int = 20  # HTTP timeout in seconds
    collector_max_story_errors: int = 15  # max story errors before ending a cycle
    collector_max_consecutive_failures: int = (
        3  # consecutive failed cycles before cooldown
    )
    collector_failure_cooldown: int = 120  # seconds to wait after repeated failures

    # Clustering
    cluster_batch_size: int = Field(
        default=400, ge=1, le=10000
    )  # documents to process in batch
    cluster_min_size: int = Field(default=3, ge=1)  # minimum documents per cluster
    cluster_schedule: int = 300  # seconds between clustering runs (0 = manual only)

    # Deduplication
    dedup_threshold: float = Field(
        default=0.85, gt=0, le=1
    )  # MinHash similarity threshold
    dedup_num_perm: int = 128  # MinHash permutations

    # Embeddings
    embedding_backend: Literal["auto", "tfidf", "semantic"] = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"  # or "cuda" if available

    # Summarization
    summary_max_sentences: int = 3
    summary_detail_sentences: int = 5

    # Logging
    log_level: str = "INFO"
    log_format: Literal["text", "json"] = "text"
    log_file: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CHRONICLE_",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def get_db_path() -> Path:
    """Get database path, creating parent directory if needed.

    Supports CHRONICLE_DB_PATH and legacy CHRONICLE_DB environment variables.
    """
    env_db_path = os.getenv("CHRONICLE_DB_PATH") or os.getenv("CHRONICLE_DB")
    db_path = Path(env_db_path or settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
