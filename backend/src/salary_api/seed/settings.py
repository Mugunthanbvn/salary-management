"""Seed settings from the environment and, locally, `.env` (docs/glossary.md section 7).

Separate from the API's Settings: `make seed-turso` builds a local SQLite file for production,
which the API's production checks rightly refuse as its own database.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from salary_api.core.config import AppEnv


class SeedSettings(BaseSettings):
    # hide_input_in_errors: a start-up error must never print the passwords it was given.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", frozen=True, hide_input_in_errors=True
    )

    # Required, like the API's: production checks can never be skipped by a missing variable.
    app_env: AppEnv
    database_url: str = "sqlite:///./dev.db"
    database_auth_token: SecretStr | None = None
    seed_admin_password: SecretStr | None = None
    seed_hr_password: SecretStr | None = None
    seed_viewer_password: SecretStr | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def password_from(self, variable: str) -> str | None:
        """The value of one SEED_*_PASSWORD variable, or None when it is not set."""
        secret = {
            "SEED_ADMIN_PASSWORD": self.seed_admin_password,
            "SEED_HR_PASSWORD": self.seed_hr_password,
            "SEED_VIEWER_PASSWORD": self.seed_viewer_password,
        }[variable]
        return None if secret is None else secret.get_secret_value()
