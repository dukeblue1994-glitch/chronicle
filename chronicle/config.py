"""Configuration management for Chronicle."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Chronicle"
    app_version: str = "0.1.0"
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
    
    # Clustering
    cluster_batch_size: int = 400  # documents to process in batch
    cluster_min_size: int = 3  # minimum documents per cluster
    cluster_schedule: int = 300  # seconds between clustering runs (0 = manual only)
    
    # Deduplication
    dedup_threshold: float = 0.85  # MinHash similarity threshold
    dedup_num_perm: int = 128  # MinHash permutations
    
    # Embeddings
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "CHRONICLE_"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def get_db_path() -> Path:
    """Get database path, creating parent directory if needed."""
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
