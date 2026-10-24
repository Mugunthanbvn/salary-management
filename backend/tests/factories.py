"""Plain builder functions for tests.

Each builder sets safe defaults, so a test states only the fields that matter to it.
Model builders (make_employee, make_salary_record, ...) are added with their models.
"""

from typing import Any

from pydantic_settings import SettingsConfigDict

from salary_api.core.config import Settings

TEST_JWT_SECRET = "test-only-jwt-secret-0123456789abcdef"


class _SettingsWithoutEnvFile(Settings):
    model_config = SettingsConfigDict(env_file=None)


def make_settings(**overrides: Any) -> Settings:
    """Settings for tests: in-memory SQLite, never read from a .env file."""
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": "sqlite://",
        "jwt_secret": TEST_JWT_SECRET,
        "cookie_secure": False,
        "cors_origins": [],
    }
    return _SettingsWithoutEnvFile(**(values | overrides))
