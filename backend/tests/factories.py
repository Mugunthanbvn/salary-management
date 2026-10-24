"""Plain builder functions for tests.

Each builder sets safe defaults, so a test states only the fields that matter to it.
Model builders (make_employee, make_salary_record, ...) are added with their models.
"""

from typing import Any

from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic_settings import SettingsConfigDict

from salary_api.core.config import Settings
from salary_api.core.security import PasswordHasher

# Low entropy on purpose, so secret scanners (gitleaks) do not mistake it for a real key.
TEST_JWT_SECRET = "test-only-" + "x" * 32

# Argon2id with the cheapest parameters, so tests hash in well under a millisecond.
# The app gets it through a dependency override (tests/conftest.py); production keeps
# pwdlib's defaults.
FAST_PASSWORD_HASHER = PasswordHasher(Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1))


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


def settings_from_environment() -> Settings:
    """Settings read only from environment variables (use with monkeypatch.setenv)."""
    # Unpacked dict: type checkers re-type the subclass __init__ with app_env required.
    from_environment_only: dict[str, Any] = {}
    return _SettingsWithoutEnvFile(**from_environment_only)
