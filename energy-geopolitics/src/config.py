"""Application configuration via environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./energy_intel.db"

    # Recovery Stack
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    retry_max_attempts: int = 3
    retry_base_delay: float = 2.0
    checkpoint_dir: str = "./checkpoints"

    # External APIs
    eia_api_key: str = ""
    news_api_key: str = ""
    alpha_vantage_key: str = ""

    # Risk Thresholds
    high_risk_threshold: float = 0.7
    critical_risk_threshold: float = 0.85

    # Alerts
    alert_webhook_url: str = ""
    alert_email: str = ""

    # Seed data
    load_seed_data: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
