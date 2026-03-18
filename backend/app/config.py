from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://biomni:changeme@localhost:5432/orenoiomni"

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

    # Auth (Phase 3)
    auth_enabled: bool = False

    @property
    def database_url_sync(self) -> str:
        """Sync DB URL for Celery workers (psycopg2 instead of asyncpg)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
