"""Build the whole seed dataset in memory, without a database (docs/12-seed-data.md).

Determinism (section 12): one `random.Random(seed)` drives every draw, in config order. Salary
history draws from a child generator seeded from it, so `--no-history` changes nothing else.
Names come from their own per-country sources (names.py). Every date is relative to
ANCHOR_DATE, never to today, and every ID is assigned here in generation order.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from salary_api.domain.compensation import total_compensation
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.domain.money import Money
from salary_api.domain.rounding import round_half_even
from salary_api.domain.search import employee_search_text
from salary_api.seed import seed_config as config
from salary_api.seed.allocation import largest_remainder
from salary_api.seed.history import HistoryEntry, back_cast, hire_only
from salary_api.seed.names import EmailBook, PersonName, name_source
from salary_api.seed.pay import (
    ComponentAmount,
    band_for,
    components_for,
    draw_noise,
    draw_uniform,
    reference_minor,
    round_to_unit,
    rounding_unit_minor,
)
from salary_api.seed.rows import (
    CountryRow,
    DepartmentRow,
    EmployeeRow,
    FxRateRow,
    JobRoleRow,
    PayBandRow,
    SalaryComponentRow,
    SalaryRecordRow,
)
from salary_api.seed.seed_config import CountrySpec, RoleSpec

_LEVELS_IN_ORDER = tuple(Level)
_MAX_TENURE_DAYS = (config.ANCHOR_DATE - config.EARLIEST_HIRE_DATE).days
_MEAN_TENURE_DAYS = config.MEAN_TENURE_YEARS * 365.25


@dataclass(frozen=True, slots=True)
class Dataset:
    """Every row the seed writes, with IDs, in insert order."""

    countries: tuple[CountryRow, ...]
    departments: tuple[DepartmentRow, ...]
    job_roles: tuple[JobRoleRow, ...]
    pay_bands: tuple[PayBandRow, ...]
    fx_rates: tuple[FxRateRow, ...]
    employees: tuple[EmployeeRow, ...]
    salary_records: tuple[SalaryRecordRow, ...]
    salary_components: tuple[SalaryComponentRow, ...]


@dataclass(frozen=True, slots=True)
class _Role:
    id: int
    department_id: int
    department: str
    spec: RoleSpec


@dataclass(slots=True)
class _Draft:
    """An employee before IDs and history: who they are and their current base pay."""

    country: CountrySpec
    role: _Role
    level: Level
    employment_type: EmploymentType
    hire_date: date
    name: PersonName
    base_minor: int
    termination_date: date | None = None


def generate(*, seed: int, employees: int, history: bool = True) -> Dataset:
    """The dataset for `seed`: `employees` people in the 10 countries, with salary history.

    The same arguments always give an equal dataset.
    """
    rng = random.Random(seed)
    history_rng = random.Random(rng.getrandbits(64))
    roles = _roles()
    drafts = _drafts(rng, seed, employees, roles)
    _terminate(rng, drafts)
    drafts.sort(key=lambda draft: draft.hire_date)  # stable: same-day hires keep their order
    employee_rows, records, components = _people(history_rng, drafts, history=history)
    return Dataset(
        countries=tuple(
            CountryRow(country.code, country.name, country.currency) for country in config.COUNTRIES
        ),
        departments=tuple(
            DepartmentRow(index, department.name)
            for index, department in enumerate(config.DEPARTMENTS, start=1)
        ),
        job_roles=tuple(
            JobRoleRow(role.id, role.spec.title, role.department_id, role.spec.family)
            for role in roles
        ),
        pay_bands=_pay_bands(roles),
        fx_rates=tuple(
            FxRateRow(currency, rate, config.FX_AS_OF, config.FX_SOURCE, _at(config.ANCHOR_DATE))
            for currency, rate in config.FX_RATES.items()
        ),
        employees=employee_rows,
        salary_records=records,
        salary_components=components,
    )


def _roles() -> list[_Role]:
    """The 35 roles with IDs in config order (department by department)."""
    roles: list[_Role] = []
    for department_id, department in enumerate(config.DEPARTMENTS, start=1):
        for spec in department.roles:
            roles.append(_Role(len(roles) + 1, department_id, department.name, spec))
    return roles


def _pay_bands(roles: Sequence[_Role]) -> tuple[PayBandRow, ...]:
    """One band per country x role x allowed level, from the pre-noise reference pay."""
    bands: list[PayBandRow] = []
    for country in config.COUNTRIES:
        for role in roles:
            for level in role.spec.levels:
                band = band_for(level, role.spec, country)
                bands.append(
                    PayBandRow(
                        id=len(bands) + 1,
                        job_role_id=role.id,
                        level=level,
                        country_code=country.code,
                        currency=country.currency,
                        min_minor=band.min_minor,
                        mid_minor=band.mid_minor,
                        max_minor=band.max_minor,
                        effective_from=config.BAND_EFFECTIVE_FROM,
                    )
                )
    return tuple(bands)


def _drafts(rng: random.Random, seed: int, total: int, roles: Sequence[_Role]) -> list[_Draft]:
    """Every employee, country by country. Departments, roles, levels and types are exact
    largest-remainder splits of the country's headcount; levels and types are shuffled."""
    drafts: list[_Draft] = []
    country_counts = largest_remainder(total, [country.share for country in config.COUNTRIES])
    for index, (country, count) in enumerate(zip(config.COUNTRIES, country_counts, strict=True)):
        names = name_source(country, seed=seed, country_index=index)
        levels = _shuffled(rng, count, [(spec.level, spec.share) for spec in config.LEVELS])
        types = _shuffled(rng, count, config.EMPLOYMENT_TYPES)
        for role, level, employment_type in zip(
            _role_slots(count, roles), levels, types, strict=True
        ):
            drafts.append(
                _draft(
                    rng,
                    country=country,
                    role=role,
                    level=_clamp(level, role.spec),
                    employment_type=employment_type,
                    name=names.next_name(),
                )
            )
    return drafts


def _role_slots(count: int, roles: Sequence[_Role]) -> list[_Role]:
    """The country's headcount split by department share, then by role weight."""
    slots: list[_Role] = []
    department_counts = largest_remainder(count, [d.share for d in config.DEPARTMENTS])
    for department, department_count in zip(config.DEPARTMENTS, department_counts, strict=True):
        department_roles = [role for role in roles if role.department == department.name]
        role_counts = largest_remainder(
            department_count, [role.spec.weight for role in department_roles]
        )
        for role, role_count in zip(department_roles, role_counts, strict=True):
            slots.extend([role] * role_count)
    return slots


def _shuffled[T](rng: random.Random, count: int, shares: Sequence[tuple[T, int]]) -> list[T]:
    """`count` values split exactly by share, in random order."""
    parts = largest_remainder(count, [share for _, share in shares])
    values = [value for (value, _), part in zip(shares, parts, strict=True) for _ in range(part)]
    rng.shuffle(values)
    return values


def _clamp(level: Level, role: RoleSpec) -> Level:
    """The nearest level the role allows (section 4)."""
    position = _LEVELS_IN_ORDER.index(level)
    lowest, highest = (_LEVELS_IN_ORDER.index(role.lowest), _LEVELS_IN_ORDER.index(role.highest))
    return _LEVELS_IN_ORDER[min(max(position, lowest), highest)]


def _draft(  # noqa: PLR0913  (one argument per fact already decided)
    rng: random.Random,
    *,
    country: CountrySpec,
    role: _Role,
    level: Level,
    employment_type: EmploymentType,
    name: PersonName,
) -> _Draft:
    """Draw the hire date and the current base: reference x log-normal noise (x part-time)."""
    hire_date = config.ANCHOR_DATE - timedelta(days=_tenure_days(rng))
    base = reference_minor(level, role.spec, country) * draw_noise(rng, config.PAY_NOISE_SIGMA)
    if employment_type == EmploymentType.PART_TIME:
        base *= draw_uniform(rng, config.PART_TIME_FACTOR)
    return _Draft(
        country=country,
        role=role,
        level=level,
        employment_type=employment_type,
        hire_date=hire_date,
        name=name,
        base_minor=round_to_unit(base, rounding_unit_minor(country)),
    )


def _tenure_days(rng: random.Random) -> int:
    """Exponential tenure with the configured mean, truncated at 11 years (never the cap itself,
    so no pile of hires on one day), and at least one day: nobody is hired on the anchor date."""
    keep = 1 - math.exp(-_MAX_TENURE_DAYS / _MEAN_TENURE_DAYS)
    days = int(-_MEAN_TENURE_DAYS * math.log(1 - rng.random() * keep))
    return min(max(days, 1), _MAX_TENURE_DAYS)


def _terminate(rng: random.Random, drafts: list[_Draft]) -> None:
    """Mark the configured share as terminated, on a day after their hire, up to the anchor."""
    count = round_half_even(len(drafts) * config.TERMINATED_SHARE)
    for index in sorted(rng.sample(range(len(drafts)), count)):
        draft = drafts[index]
        days = (config.ANCHOR_DATE - draft.hire_date).days
        draft.termination_date = draft.hire_date + timedelta(days=rng.randint(1, days))


def _people(
    rng: random.Random, drafts: Sequence[_Draft], *, history: bool
) -> tuple[tuple[EmployeeRow, ...], tuple[SalaryRecordRow, ...], tuple[SalaryComponentRow, ...]]:
    """Employee, salary record and component rows, with IDs in hire order."""
    emails = EmailBook()
    employees: list[EmployeeRow] = []
    records: list[SalaryRecordRow] = []
    components: list[SalaryComponentRow] = []
    for employee_id, draft in enumerate(drafts, start=1):
        code = f"{config.EMPLOYEE_CODE_PREFIX}{employee_id:06d}"
        email = emails.email_for(draft.name, code)
        for entry in _history(rng, draft, history=history):
            parts = components_for(
                entry.base_minor,
                level=entry.level,
                role=draft.role.spec,
                country=draft.country,
                employment_type=draft.employment_type,
            )
            record_id = len(records) + 1
            for part in parts:
                components.append(
                    SalaryComponentRow(
                        len(components) + 1, record_id, part.type, part.name, part.amount_minor
                    )
                )
            records.append(
                SalaryRecordRow(
                    id=record_id,
                    employee_id=employee_id,
                    effective_date=entry.effective_date,
                    currency=draft.country.currency,
                    base_minor=entry.base_minor,
                    total_minor=_total_minor(draft.country.currency, entry.base_minor, parts),
                    job_role_id=draft.role.id,
                    level=entry.level,
                    reason=entry.reason,
                    created_at=_at(entry.effective_date),
                )
            )
        employees.append(_employee_row(employee_id, code, email, draft, records[-1]))
    return tuple(employees), tuple(records), tuple(components)


def _history(rng: random.Random, draft: _Draft, *, history: bool) -> list[HistoryEntry]:
    if not history:
        return hire_only(
            hire_date=draft.hire_date, current_base_minor=draft.base_minor, level=draft.level
        )
    return back_cast(
        rng,
        hire_date=draft.hire_date,
        end_date=draft.termination_date or config.ANCHOR_DATE,
        current_base_minor=draft.base_minor,
        current_level=draft.level,
        allowed_levels=draft.role.spec.levels,
        unit_minor=rounding_unit_minor(draft.country),
    )


def _total_minor(currency: str, base_minor: int, parts: Sequence[ComponentAmount]) -> int:
    """Base + every component (domain/compensation.py), all in the record's currency."""
    components = (Money(part.amount_minor, currency) for part in parts)
    return total_compensation(Money(base_minor, currency), components).amount_minor


def _employee_row(
    employee_id: int, code: str, email: str, draft: _Draft, current: SalaryRecordRow
) -> EmployeeRow:
    """The employee, with the current salary copied from their latest record (docs/06 6.2)."""
    terminated = draft.termination_date is not None
    last_change = max(current.effective_date, draft.termination_date or current.effective_date)
    return EmployeeRow(
        id=employee_id,
        employee_code=code,
        first_name=draft.name.first_name,
        last_name=draft.name.last_name,
        email=email,
        search_text=employee_search_text(draft.name.first_name, draft.name.last_name, code, email),
        job_role_id=draft.role.id,
        level=current.level,
        employment_type=draft.employment_type,
        country_code=draft.country.code,
        status=EmployeeStatus.TERMINATED if terminated else EmployeeStatus.ACTIVE,
        hire_date=draft.hire_date,
        termination_date=draft.termination_date,
        currency=current.currency,
        current_base_minor=current.base_minor,
        current_total_minor=current.total_minor,
        current_salary_record_id=current.id,
        created_at=_at(draft.hire_date),
        updated_at=_at(last_change),
    )


def _at(day: date) -> datetime:
    """Midnight UTC of `day`: seeded timestamps come from dates, never from the clock."""
    return datetime.combine(day, time(tzinfo=UTC))
