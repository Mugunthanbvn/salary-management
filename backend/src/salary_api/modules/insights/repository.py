"""Insight queries: the filtered population's grouping keys and amounts, sorted.

The database filters, sorts and returns only the columns a statistic needs; Python does
the maths (docs/19-performance.md section 4.2).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, Row, Select, select
from sqlalchemy.orm import QueryableAttribute, Session, contains_eager

from salary_api.core.schemas import Comp
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.repository import AMOUNT_COLUMNS
from salary_api.modules.reference.models import Country, Department, FxRate, JobRole


@dataclass(frozen=True, slots=True)
class PopulationFilter:
    """Which employees an insight covers. An empty sequence means no condition on that field."""

    countries: Sequence[str] = ()
    department_ids: Sequence[int] = ()
    job_role_ids: Sequence[int] = ()
    levels: Sequence[Level] = ()
    employment_types: Sequence[EmploymentType] = ()
    statuses: Sequence[EmployeeStatus] = ()


@dataclass(frozen=True, slots=True)
class CountryMarket:
    """A country's salary currency and that currency's USD rate (None when it has none)."""

    code: str
    currency: str
    rate_to_usd: str | None
    as_of: date | None


def countries_and_rates(session: Session) -> list[CountryMarket]:
    """Every country with its currency's USD rate, in one query (an outer join)."""
    query = (
        select(Country.code, Country.default_currency, FxRate.rate_to_usd, FxRate.as_of)
        .outerjoin(FxRate, FxRate.currency == Country.default_currency)
        .order_by(Country.code)
    )
    return [CountryMarket(*row) for row in session.execute(query)]


def amounts_by_country(
    session: Session, where: PopulationFilter, comp: Comp
) -> Sequence[Row[str, str, int]]:
    """(country code, currency, amount) per employee, by country then amount."""
    amount = AMOUNT_COLUMNS[comp]
    query = _matching(select(Employee.country_code, Employee.currency, amount), where).order_by(
        Employee.country_code, amount
    )
    return session.execute(query).all()


def employee_ids(session: Session, where: PopulationFilter) -> set[int]:
    """The ids of the employees in a population."""
    return set(session.scalars(_matching(select(Employee.id), where)).all())


def amounts_by_department(
    session: Session, where: PopulationFilter, comp: Comp
) -> Sequence[Row[int, str, str, int]]:
    """(department id, department name, currency, amount) per employee, by name then amount."""
    amount = AMOUNT_COLUMNS[comp]
    query = (
        _matching(select(Department.id, Department.name, Employee.currency, amount), where)
        .join(JobRole.department)
        .order_by(Department.name, Department.id, amount)
    )
    return session.execute(query).all()


def amounts_by_job_role(
    session: Session, where: PopulationFilter, comp: Comp
) -> Sequence[Row[int, str, int, Level, str, int]]:
    """(job role id, title, department id, level, currency, amount) per employee, by title,
    level, amount."""
    amount = AMOUNT_COLUMNS[comp]
    query = _matching(
        select(
            JobRole.id,
            JobRole.title,
            JobRole.department_id,
            Employee.level,
            Employee.currency,
            amount,
        ),
        where,
    ).order_by(JobRole.title, JobRole.id, Employee.level, amount)
    return session.execute(query).all()


def pay_rows(
    session: Session, where: PopulationFilter
) -> Sequence[Row[int, str, int, str, Level, str, EmploymentType, str, int]]:
    """What pay equity needs per employee: (department id, department name, job role id,
    title, level, country code, employment type, currency, base)."""
    query = _matching(
        select(
            Department.id,
            Department.name,
            JobRole.id,
            JobRole.title,
            Employee.level,
            Employee.country_code,
            Employee.employment_type,
            Employee.currency,
            Employee.current_base_minor,
        ),
        where,
    ).join(JobRole.department)
    return session.execute(query).all()


def members(session: Session, where: PopulationFilter) -> Sequence[Employee]:
    """The matching employees, by employee code."""
    query = _matching(select(Employee), where).order_by(Employee.employee_code)
    return session.scalars(query).all()


def ranked(
    session: Session, where: PopulationFilter, comp: Comp, *, descending: bool, limit: int
) -> Sequence[Employee]:
    """The `limit` highest (or lowest) paid employees with role and department loaded.

    Ties are broken by employee code, so the ranking is always the same.
    """
    amount = AMOUNT_COLUMNS[comp]
    query = (
        _matching(select(Employee), where)
        .join(JobRole.department)
        .options(contains_eager(Employee.job_role).contains_eager(JobRole.department))
        .order_by(amount.desc() if descending else amount.asc(), Employee.employee_code)
        .limit(limit)
    )
    return session.scalars(query).all()


def _matching[*Row](query: Select[*Row], where: PopulationFilter) -> Select[*Row]:
    return query.select_from(Employee).join(Employee.job_role).where(*_conditions(where))


def _conditions(where: PopulationFilter) -> list[ColumnElement[bool]]:
    candidates = [
        _any_of(Employee.country_code, where.countries),
        _any_of(JobRole.department_id, where.department_ids),
        _any_of(Employee.job_role_id, where.job_role_ids),
        _any_of(Employee.level, where.levels),
        _any_of(Employee.employment_type, where.employment_types),
        _any_of(Employee.status, where.statuses),
    ]
    return [condition for condition in candidates if condition is not None]


def _any_of[T](column: QueryableAttribute[T], values: Sequence[T]) -> ColumnElement[bool] | None:
    """`column IN (values)`, or no condition when no value is asked for."""
    return column.in_(values) if values else None
