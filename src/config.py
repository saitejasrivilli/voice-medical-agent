"""
Configuration management for the application.
Loads from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Application
    app_name: str = "Medical Voice Agent"
    app_version: str = "1.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = False

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Groq API
    groq_api_key: str = ""  # Required - must be set via env
    groq_timeout_seconds: int = 30
    groq_model: str = "whisper-large-v3"

    # Database
    database_url: str = "sqlite:///./medical_agent.db"
    # Postgres example: postgresql://user:password@localhost/dbname
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False  # Log SQL queries if True

    # Audio processing
    max_audio_size_mb: int = 25
    supported_audio_formats: list = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/webm"]
    audio_temp_dir: str = "${TMPDIR:-/tmp}/medical_agent_audio"

    # Rate limiting
    rate_limit_per_minute: int = 10
    rate_limit_per_hour: int = 100

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Retention policies
    assessment_retention_days: int = 90
    audit_log_retention_days: int = 365

    # Feature flags
    enable_specialty_routing: bool = True
    enable_agent_responses: bool = True
    enable_metrics_collection: bool = True
    enable_audit_logging: bool = True

    # Security
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]

    # Routing confidence thresholds
    routing_confidence_threshold: float = 0.65
    min_confidence_to_proceed: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
settings = Settings()
