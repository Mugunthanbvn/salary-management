"""API configuration from environment variables (docs/glossary.md section 7)."""

from typing import Annotated, Any, Literal, Self

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_core import InitErrorDetails
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import make_url

type AppEnv = Literal["development", "test", "production"]
type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

# The documented development value of JWT_SECRET (backend/.env.example).
DEV_PLACEHOLDER = "dev-change-me"
# Production refuses a JWT_SECRET that contains any of these, whatever its length.
PLACEHOLDER_MARKERS = ("change-me", "changeme", "dev-only", "test-only")
MIN_SECRET_BYTES = 32


class Settings(BaseSettings):
    """Validated settings. Read from the environment and, locally, from `.env`."""

    # hide_input_in_errors: a start-up error must never print the secrets it was given.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", frozen=True, hide_input_in_errors=True
    )

    def __init__(self, **values: Any) -> None:
        try:
            super().__init__(**values)
        except ValidationError as error:
            # `from None`: the original error, which holds the inputs, is not chained.
            raise _without_inputs(error) from None

    # Required, so production checks can never be skipped by a missing variable.
    app_env: AppEnv
    database_url: str = "sqlite:///./dev.db"
    database_auth_token: SecretStr | None = None
    jwt_secret: SecretStr = SecretStr(DEV_PLACEHOLDER)
    jwt_ttl_minutes: int = Field(default=480, gt=0)
    cookie_secure: bool = False
    # Comma-separated in the environment: CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list[str])
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    ask_rate_limit_per_hour: int = Field(default=20, gt=0)
    ask_max_steps: int = Field(default=4, gt=0)
    log_level: LogLevel = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _refuse_unsafe_production_values(self) -> Self:
        if self.app_env == "production" and (problems := _production_problems(self)):
            raise ValueError("Unsafe settings for APP_ENV=production: " + "; ".join(problems))
        return self


def load_settings() -> Settings:
    """Settings from the environment and `.env`. Fails if APP_ENV is missing."""
    return Settings()


def _without_inputs(error: ValidationError) -> ValidationError:
    """The same errors with every input value hidden, also in `errors()`."""
    details: list[InitErrorDetails] = []
    for item in error.errors(include_url=False):
        detail: InitErrorDetails = {"type": item["type"], "loc": item["loc"], "input": "[hidden]"}
        if "ctx" in item:
            detail["ctx"] = item["ctx"]
        details.append(detail)
    return ValidationError.from_exception_data(error.title, details, hide_input=True)


def _production_problems(settings: Settings) -> list[str]:
    problems: list[str] = []
    if _is_weak_secret(settings.jwt_secret.get_secret_value()):
        problems.append(
            f"JWT_SECRET must be at least {MIN_SECRET_BYTES} random bytes, not a placeholder"
        )
    if not settings.cookie_secure:
        problems.append("COOKIE_SECURE must be true")
    if _is_local_sqlite(settings.database_url):
        problems.append("DATABASE_URL must be a hosted database, not a local or in-memory SQLite")
    if settings.cors_origins:
        problems.append("CORS_ORIGINS must be empty (the browser uses the same-origin rewrite)")
    return problems


def _is_local_sqlite(database_url: str) -> bool:
    """A SQLite URL without a host is a file on this machine or in memory."""
    url = make_url(database_url)
    return url.get_backend_name() == "sqlite" and not url.host


def _is_weak_secret(secret: str) -> bool:
    lowered = secret.lower()
    return len(secret.encode()) < MIN_SECRET_BYTES or any(
        marker in lowered for marker in PLACEHOLDER_MARKERS
    )
