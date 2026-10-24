"""Run the seed: check, migrate, generate, load, report (docs/12-seed-data.md sections 13-14).

Every refusal happens before the database is touched, so a refused seed creates no file.
"""

import time
from collections import Counter
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TextIO

from sqlalchemy import make_url

from salary_api.core.db import create_engine_for_url
from salary_api.core.security import PasswordHasher
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.seed import seed_config as config
from salary_api.seed.errors import SeedRefused
from salary_api.seed.generator import Dataset, generate
from salary_api.seed.loader import checkpoint, load, migrate
from salary_api.seed.settings import SeedSettings
from salary_api.seed.users import demo_users

_COUNTRY_ORDER = [country.code for country in config.COUNTRIES]
_DEPARTMENTS = [department.name for department in config.DEPARTMENTS]


@dataclass(frozen=True, slots=True)
class SeedOptions:
    """The command-line options (docs/12 section 14)."""

    seed: int = 42
    employees: int = 10_000
    reset: bool = False
    story: bool = True
    history: bool = True
    db_url: str | None = None  # DATABASE_URL when not given
    force_demo: bool = False


def run_seed(
    options: SeedOptions, settings: SeedSettings, *, hasher: PasswordHasher, out: TextIO
) -> Dataset:
    """Seed the database and write a summary with timings to `out`.

    Raises SeedRefused for a production reset without `force_demo`, for unsafe production
    passwords, and for a database that has data when `reset` is off.
    """
    if settings.is_production and options.reset and not options.force_demo:
        raise SeedRefused(
            "APP_ENV=production: --reset deletes every row. "
            "Pass --force-demo as well to replace demo data."
        )
    clock = _Stopwatch()
    with clock.phase("users"):
        users = demo_users(settings, hasher)  # refuses unsafe production passwords
    database_url = options.db_url or settings.database_url
    token = settings.database_auth_token
    engine = create_engine_for_url(
        database_url, auth_token=token.get_secret_value() if token else None
    )
    try:
        with clock.phase("migrate"):
            migrate(engine)
        with clock.phase("generate"):
            dataset = generate(
                seed=options.seed,
                employees=options.employees,
                story=options.story,
                history=options.history,
            )
        with clock.phase("insert"):
            with engine.begin() as connection:
                load(connection, dataset, users, reset=options.reset)
            checkpoint(engine)
    finally:
        engine.dispose()
    shown_url = make_url(database_url).render_as_string(hide_password=True)
    out.write(summary(dataset, seed=options.seed, database=shown_url, users=len(users)))
    out.write(clock.report() + "\n")
    return dataset


def summary(dataset: Dataset, *, seed: int, database: str, users: int) -> str:
    """Counts per country, department, level and type, and the size of every table."""
    departments = {d.id: d.name for d in dataset.departments}
    department_of = {role.id: departments[role.department_id] for role in dataset.job_roles}
    employees = dataset.employees
    story = dataset.story
    planted = (
        f"{len(story.underpaid_ids):,} underpaid + {len(story.overpaid_ids):,} overpaid "
        f"outliers; {len(story.pay_gap_ids):,} {config.PAY_GAP_COUNTRY} "
        f"{config.PAY_GAP_DEPARTMENT} at x{config.PAY_GAP_FACTOR}"
        if story.pay_gap_ids or story.underpaid_ids or story.overpaid_ids
        else "off"
    )
    rows = [
        ("status", _counts((e.status for e in employees), list(EmployeeStatus))),
        ("countries", _counts((e.country_code for e in employees), _COUNTRY_ORDER)),
        ("departments", _counts((department_of[e.job_role_id] for e in employees), _DEPARTMENTS)),
        ("levels", _counts((e.level for e in employees), list(Level))),
        ("types", _counts((e.employment_type for e in employees), list(EmploymentType))),
        ("salary records", f"{len(dataset.salary_records):,}"),
        ("components", f"{len(dataset.salary_components):,}"),
        ("pay bands", f"{len(dataset.pay_bands):,}"),
        ("fx rates", f"{len(dataset.fx_rates):,}"),
        ("users", f"{users:,}"),
        ("demo story", planted),
    ]
    heading = f"Seeded {len(employees):,} employees (seed {seed}) into {database}\n"
    return heading + "".join(f"  {name:<15} {value}\n" for name, value in rows)


def _counts(values: Iterable[str], order: Sequence[str]) -> str:
    """`US 3,000  IN 2,500 ...` in the given order, leaving out zeros."""
    counts = Counter(values)
    return "  ".join(f"{key} {counts[key]:,}" for key in order if counts[key])


@dataclass(slots=True)
class _Stopwatch:
    phases: list[tuple[str, float]] = field(default_factory=list[tuple[str, float]])
    started: float = field(default_factory=time.perf_counter)

    @contextmanager
    def phase(self, name: str) -> Generator[None]:
        start = time.perf_counter()
        yield
        self.phases.append((name, time.perf_counter() - start))

    def report(self) -> str:
        total = time.perf_counter() - self.started
        parts = [f"{name} {seconds:.2f} s" for name, seconds in self.phases]
        return f"  {'time':<15} " + "  ".join([*parts, f"total {total:.2f} s"])
