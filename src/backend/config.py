from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    exa_api_key: str
    resend_api_key: str
    database_url: str = "postgresql+asyncpg://portco:portco@localhost:5432/portco_monitoring"

    # Pipeline
    relevance_threshold: float = 6.0
    max_developments_per_company: int = 10
    exa_results_per_query: int = 10

    # Email
    email_from: str = "Ana Llana <ana@stuhi.co>"
    app_base_url: str = "http://localhost:8000"

    # Scheduler
    digest_cron_hour: int = 8
    digest_cron_day_of_week: str = "mon"

    # LLM
    claude_model: str = "claude-haiku-4-5-20251001"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore[call-arg]
