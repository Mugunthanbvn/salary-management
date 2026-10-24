"""API configuration from environment variables (docs/glossary.md section 7)."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

type AppEnv = Literal["development", "test", "production"]
type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

# The documented development value of JWT_SECRET (backend/.env.example).
DEV_PLACEHOLDER = "dev-only-change-me"


class Settings(BaseSettings):
    """Validated settings. Read from the environment and, locally, from `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    app_env: AppEnv = "development"
    database_url: str = "sqlite:///./dev.db"
    database_auth_token: SecretStr | None = None
    jwt_secret: SecretStr = SecretStr(DEV_PLACEHOLDER)
    jwt_ttl_minutes: int = Field(default=480, gt=0)
    cookie_secure: bool = False
    cors_origins: list[str] = Field(default_factory=list[str])
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    ask_rate_limit_per_hour: int = Field(default=20, gt=0)
    ask_max_steps: int = Field(default=4, gt=0)
    log_level: LogLevel = "INFO"
