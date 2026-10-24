"""Plain builder functions for tests.

Each builder sets safe defaults, so a test states only the fields that matter to it.
Model builders (make_employee, make_salary_record, ...) are added with their models.
"""

from collections.abc import Sequence
from datetime import date
from itertools import count
from typing import Any

from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic_settings import SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.permissions import Role
from salary_api.core.security import PasswordHasher
from salary_api.domain.enums import (
    ComponentType,
    EmployeeStatus,
    EmploymentType,
    Level,
    SalaryReason,
)
from salary_api.domain.rounding import divide_half_even
from salary_api.domain.search import employee_search_text
from salary_api.modules.employees import repository as employees
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import (
    Country,
    Department,
    FxRate,
    JobFamily,
    JobRole,
    PayBand,
)
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.users.models import User
from salary_api.seed.settings import SeedSettings

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


class _SeedSettingsWithoutEnvFile(SeedSettings):
    model_config = SettingsConfigDict(env_file=None)


def make_seed_settings(**overrides: Any) -> SeedSettings:
    """Seed settings for tests: in-memory SQLite, no passwords set unless given, no .env file.

    Every value is passed explicitly, so a SEED_*_PASSWORD in the shell cannot leak in.
    """
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": "sqlite://",
        "seed_admin_password": None,
        "seed_hr_password": None,
        "seed_viewer_password": None,
    }
    return _SeedSettingsWithoutEnvFile(**(values | overrides))


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


def employee_request(job_role_id: int, **overrides: Any) -> dict[str, Any]:
    """A valid POST /employees body for a new employee in Germany (EUR), hired 2026-09-01."""
    body: dict[str, Any] = {
        "first_name": "Lena",
        "last_name": "Müller",
        "email": "lena.mueller@acme.example",
        "job_role_id": job_role_id,
        "level": "L2",
        "employment_type": "FULL_TIME",
        "country_code": "DE",
        "hire_date": "2026-09-01",
        "salary": {
            "base_minor": 5_400_000,
            "components": [
                {"type": "ALLOWANCE", "name": "Transport", "amount_minor": 60_000},
                {"type": "BONUS_TARGET", "name": "Target bonus", "amount_minor": 432_000},
            ],
            "note": "Offer accepted 2026-08-12",
        },
    }
    return body | overrides


_employee_numbers = count(1)

# (type, name, amount_minor), e.g. ("ALLOWANCE", "HRA", 72_000_000).
type ComponentSpec = tuple[ComponentType | str, str, int]


def make_employee(
    session: Session,
    *,
    country: str = "DE",
    job_role: JobRole | None = None,
    level: Level | str = Level.L3,
    employment_type: EmploymentType | str = EmploymentType.FULL_TIME,
    base_minor: int = 6_000_000,
    components: Sequence[ComponentSpec] = (),
    first_name: str = "Test",
    last_name: str | None = None,
    email: str | None = None,
    employee_code: str | None = None,
    hire_date: date = date(2024, 1, 15),
    status: EmployeeStatus | str = EmployeeStatus.ACTIVE,
    termination_date: date | None = None,
    changed_by: User | None = None,
) -> Employee:
    """A saved employee with its HIRE salary record, paid in the country's currency.

    The current-salary columns match the record, as the salary service keeps them.
    """
    currency = make_country(session, country).default_currency
    role = job_role or make_job_role(session)
    number = next(_employee_numbers)
    code = employee_code or _next_code(session)
    last_name = last_name or f"Employee {number}"
    email = email or f"employee-{number}@acme.example"
    total_minor = base_minor + sum(amount for _type, _name, amount in components)
    status = EmployeeStatus(status)
    employee = Employee(
        employee_code=code,
        first_name=first_name,
        last_name=last_name,
        email=email,
        search_text=employee_search_text(first_name, last_name, code, email),
        job_role_id=role.id,
        level=Level(level),
        employment_type=EmploymentType(employment_type),
        country_code=country,
        status=status,
        hire_date=hire_date,
        termination_date=termination_date
        or (hire_date if status == EmployeeStatus.TERMINATED else None),
        currency=currency,
        current_base_minor=base_minor,
        current_total_minor=total_minor,
    )
    session.add(employee)
    session.flush()
    record = SalaryRecord(
        employee_id=employee.id,
        effective_date=hire_date,
        currency=currency,
        base_minor=base_minor,
        total_minor=total_minor,
        job_role_id=role.id,
        level=employee.level,
        reason=SalaryReason.HIRE,
        changed_by=changed_by.id if changed_by else None,
        components=[
            SalaryComponent(type=ComponentType(kind), name=name, amount_minor=amount)
            for kind, name, amount in components
        ],
    )
    session.add(record)
    session.flush()
    employee.current_salary_record_id = record.id
    session.flush()
    return employee


def _next_code(session: Session) -> str:
    highest = employees.highest_employee_code(session)
    return f"ACME-{int(highest.removeprefix('ACME-')) + 1 if highest else 1:06d}"


# Illustrative USD rates (USD per major unit), like the seed's static snapshot.
USD_RATES = {
    "USD": "1",
    "EUR": "1.085",
    "GBP": "1.27",
    "INR": "0.01198",
    "JPY": "0.0067",
    "CAD": "0.73",
    "AUD": "0.66",
    "SGD": "0.74",
    "BRL": "0.18",
}
FX_AS_OF = date(2026, 10, 1)


def make_fx_rate(
    session: Session, currency: str, rate_to_usd: str | None = None, *, as_of: date = FX_AS_OF
) -> FxRate:
    """The USD rate of `currency` (USD_RATES by default), created on first use."""
    existing = session.get(FxRate, currency)
    if existing is not None:
        return existing
    rate = FxRate(
        currency=currency,
        rate_to_usd=rate_to_usd or USD_RATES[currency],
        as_of=as_of,
        source="Static snapshot (illustrative)",
    )
    session.add(rate)
    session.flush()
    return rate


def make_fx_rates(session: Session) -> list[FxRate]:
    """A USD rate for every supported currency."""
    return [make_fx_rate(session, currency) for currency in USD_RATES]


def make_pay_band(
    session: Session,
    *,
    job_role: JobRole | None = None,
    level: Level | str = Level.L3,
    country: str = "DE",
    mid_minor: int = 6_000_000,
    min_minor: int | None = None,
    max_minor: int | None = None,
    effective_from: date = date(2026, 1, 1),
) -> PayBand:
    """A saved pay band in the country's currency; min and max default to 0.8 and 1.2 x mid
    (the seed's band width, docs/glossary.md section 3), rounded half-even."""
    band = PayBand(
        job_role_id=(job_role or make_job_role(session)).id,
        level=Level(level),
        country_code=country,
        currency=make_country(session, country).default_currency,
        min_minor=min_minor if min_minor is not None else divide_half_even(mid_minor * 8, 10),
        mid_minor=mid_minor,
        max_minor=max_minor if max_minor is not None else divide_half_even(mid_minor * 12, 10),
        effective_from=effective_from,
    )
    session.add(band)
    session.flush()
    return band
