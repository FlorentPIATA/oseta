"""OSETA — Configuration via Pydantic Settings.

Usage: from config import settings
JAMAIS os.environ directement.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),  # .env.local surcharge .env
        extra="ignore",
    )

    # Database
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_correlation: int = 21600
    redis_ttl_llm: int = 86400
    redis_ttl_sectors: int = 43200

    # LLM
    openai_api_key: str = ""
    google_api_key: str = ""
    litellm_default_model: str = "gpt-4o-mini"
    litellm_premium_model: str = "gpt-4o"
    litellm_premium_threshold_is: float = 80.0
    llm_daily_budget_usd: float = 50.0

    # External APIs
    fred_api_key: str = ""
    alpha_vantage_api_key: str = ""
    brave_api_key: str = ""
    eventregistry_api_key: str = ""
    bing_api_key: str = ""

    # Auth
    secret_key: str = "changeme"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080

    # Prefect
    prefect_api_url: str = "http://localhost:4200/api"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default=["http://localhost:5173"])
    oseta_master_key: str = "changeme"

    # Scoring thresholds
    ci_publish_threshold: float = 65.0
    is_alert_threshold: float = 80.0
    cp_action_threshold: float = 80.0

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
