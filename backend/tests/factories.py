"""Plain builder functions for tests.

Each builder sets safe defaults, so a test states only the fields that matter to it.
Model builders (make_employee, make_salary_record, ...) are added with their models.
"""

from itertools import count
from typing import Any

from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic_settings import SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.permissions import Role
from salary_api.core.security import PasswordHasher
from salary_api.modules.reference.models import Country, Department, JobFamily, JobRole
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


# The ten seeded countries (docs/12-seed-data.md section 2).
COUNTRY_NAMES_AND_CURRENCIES = {
    "US": ("United States", "USD"),
    "IN": ("India", "INR"),
    "GB": ("United Kingdom", "GBP"),
    "DE": ("Germany", "EUR"),
    "CA": ("Canada", "CAD"),
    "FR": ("France", "EUR"),
    "SG": ("Singapore", "SGD"),
    "AU": ("Australia", "AUD"),
    "JP": ("Japan", "JPY"),
    "BR": ("Brazil", "BRL"),
}


def make_country(
    session: Session,
    code: str = "DE",
    *,
    name: str | None = None,
    default_currency: str | None = None,
    is_active: bool = True,
) -> Country:
    """The country with this code, created on first use and returned unchanged after that.

    A seeded code gets its seeded name and currency; another code needs `default_currency`.
    """
    existing = session.get(Country, code)
    if existing is not None:
        return existing
    seeded_name, seeded_currency = COUNTRY_NAMES_AND_CURRENCIES.get(code, (code, None))
    currency = default_currency or seeded_currency
    if currency is None:
        raise ValueError(f"make_country({code!r}) needs a default_currency")
    country = Country(
        code=code, name=name or seeded_name, default_currency=currency, is_active=is_active
    )
    session.add(country)
    session.flush()
    return country


def make_department(session: Session, name: str = "Engineering") -> Department:
    """The department with this name, created on first use."""
    existing = session.scalars(select(Department).where(Department.name == name)).one_or_none()
    if existing is not None:
        return existing
    department = Department(name=name)
    session.add(department)
    session.flush()
    return department


def make_job_role(
    session: Session,
    title: str = "Software Engineer",
    *,
    department: Department | None = None,
    family: JobFamily = JobFamily.ENGINEERING,
) -> JobRole:
    """The job role with this title, created on first use (in Engineering by default)."""
    existing = session.scalars(select(JobRole).where(JobRole.title == title)).one_or_none()
    if existing is not None:
        return existing
    role = JobRole(title=title, department=department or make_department(session), family=family)
    session.add(role)
    session.flush()
    return role
