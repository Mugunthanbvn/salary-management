"""Insight queries: the filtered population's grouping keys and amounts, sorted.

The database filters, sorts and returns only the columns a statistic needs; Python does
the maths (docs/19-performance.md section 4.2).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import QueryableAttribute, Session

from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import JobRole


@dataclass(frozen=True, slots=True)
class PopulationFilter:
    """Which employees an insight covers. An empty sequence means no condition on that field."""

    countries: Sequence[str] = ()
    department_ids: Sequence[int] = ()
    job_role_ids: Sequence[int] = ()
    levels: Sequence[Level] = ()
    employment_types: Sequence[EmploymentType] = ()
    statuses: Sequence[EmployeeStatus] = ()


def headcount(session: Session, where: PopulationFilter) -> int:
    return session.scalar(_matching(select(func.count(Employee.id)), where)) or 0


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
