from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    exa_api_key: str
    resend_api_key: str
    database_url: str = "postgresql+asyncpg://portco:portco@localhost:5432/portco_monitoring"

    # Pipeline
    relevance_threshold: float = 6.5
    max_developments_per_company: int = 5
    exa_results_per_query: int = 7
    max_key_developments: int = 3
    max_notable_developments: int = 2

    # Subscription limits
    max_companies_per_subscription: int = 10
    digest_cooldown_hours: int = 1

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Email
    email_from: str = "Ana Llana <ana@stuhi.co>"
    app_base_url: str = "http://localhost:8000"

    # Auth
    frontend_base_url: str = "http://localhost:3000"
    magic_link_ttl_minutes: int = 15
    session_ttl_days: int = 30

    # LLM
    claude_model: str = "claude-haiku-4-5-20251001"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore[call-arg]
