import logging
import sys

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_VALID_SOURCES = {"Ollama", "Anthropic", "OpenAI", "Custom"}


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://biomni:changeme@localhost:5432/orenoiomni"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour

    # Agent
    biomni_llm: str = "qwen3.5:35b-a3b-q8_0"
    biomni_source: str = "Ollama"
    biomni_data_path: str = "./data"
    biomni_timeout_seconds: int = 600
    biomni_use_tool_retriever: bool = False
    biomni_custom_base_url: str | None = None
    biomni_custom_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # API keys (for cloud LLM providers)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:7860"]

    # Celery / Redis
    redis_url: str = "redis://redis:6379/0"
    celery_task_timeout: int = 600
    workspace_base_path: str = "/data/workspaces"

    # Sandbox execution
    sandbox_enabled: bool = False  # When False, execute directly (backward compatible)
    sandbox_image_python: str = "orenoiomni-sandbox:latest"
    sandbox_image_r: str = "orenoiomni-sandbox:latest"
    sandbox_image_bash: str = "orenoiomni-sandbox:latest"
    sandbox_cpus: float = 2.0  # CPU limit per container
    sandbox_memory: str = "4g"  # Memory limit per container
    sandbox_network_disabled: bool = True  # Disable network in sandbox (security)
    sandbox_tmpfs_size: str = "512m"  # tmpfs /tmp size

    # Auth (Phase 3)
    auth_enabled: bool = False
    auth_secret: str = "change-me-in-production"  # JWT signing secret
    google_client_id: str | None = None
    google_client_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None
    auth_redirect_url: str = "http://localhost:3000"

    @model_validator(mode="after")
    def validate_source_and_keys(self):
        if self.biomni_source not in _VALID_SOURCES:
            raise ValueError(
                f"BIOMNI_SOURCE must be one of {_VALID_SOURCES}, got '{self.biomni_source}'"
            )
        if self.biomni_source == "Anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when BIOMNI_SOURCE=Anthropic")
        if self.biomni_source == "OpenAI" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when BIOMNI_SOURCE=OpenAI")
        if self.biomni_source == "Custom" and not self.biomni_custom_base_url:
            raise ValueError("BIOMNI_CUSTOM_BASE_URL is required when BIOMNI_SOURCE=Custom")
        return self

    @property
    def database_url_sync(self) -> str:
        """Sync DB URL for Celery workers (psycopg2 instead of asyncpg)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


try:
    settings = Settings()
except Exception as e:
    logger.critical("Configuration error: %s", e)
    print(f"\n  Configuration error: {e}\n", file=sys.stderr)
    sys.exit(1)
