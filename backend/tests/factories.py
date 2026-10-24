"""Plain builder functions for tests.

Each builder sets safe defaults, so a test states only the fields that matter to it.
Model builders (make_employee, make_salary_record, ...) are added with their models.
"""

from itertools import count
from typing import Any

from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic_settings import SettingsConfigDict
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.permissions import Role
from salary_api.core.security import PasswordHasher
from salary_api.modules.users.models import User

# Low entropy on purpose, so secret scanners (gitleaks) do not mistake it for a real key.
TEST_JWT_SECRET = "test-only-" + "x" * 32

# Argon2id with the cheapest parameters, so tests hash in well under a millisecond.
# The app gets it through a dependency override (tests/conftest.py); production keeps
# pwdlib's defaults.
FAST_ARGON2 = Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1)
FAST_PASSWORD_HASHER = PasswordHasher(FAST_ARGON2)


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


DEFAULT_PASSWORD = "correct horse battery staple"
_user_numbers = count(1)


def make_user(
    session: Session,
    *,
    role: Role | str = Role.VIEWER,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    full_name: str | None = None,
    is_active: bool = True,
) -> User:
    """A saved (flushed) user whose password is `password`, hashed with FAST_PASSWORD_HASHER."""
    role = Role(role)
    number = next(_user_numbers)
    user = User(
        email=email or f"{role.lower()}-{number}@acme.example",
        full_name=full_name or f"Test {role.title()} {number}",
        password_hash=FAST_PASSWORD_HASHER.hash(password),
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user
