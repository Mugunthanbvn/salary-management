from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, and_, false, func, or_, select
from sqlalchemy.orm import QueryableAttribute, Session, contains_eager, joinedload

from salary_api.core.schemas import Comp
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import JobRole
from salary_api.modules.salaries.models import SalaryRecord


def add(session: Session, employee: Employee) -> None:
    session.add(employee)
    session.flush()


def get_detail(session: Session, employee_id: int) -> Employee | None:
    """The employee with its role, department and current salary record loaded."""
    query = (
        select(Employee)
        .where(Employee.id == employee_id)
        .options(
            joinedload(Employee.job_role).joinedload(JobRole.department),
            joinedload(Employee.current_salary_record).selectinload(SalaryRecord.components),
        )
    )
    return session.scalars(query).one_or_none()


def highest_employee_code(session: Session) -> str | None:
    """The greatest `ACME-######` code. Codes have a fixed width, so text order is number order."""
    return session.scalar(
        select(func.max(Employee.employee_code)).where(Employee.employee_code.like("ACME-%"))
    )


def code_in_use(session: Session, employee_code: str) -> bool:
    return (
        session.scalar(select(Employee.id).where(Employee.employee_code == employee_code))
        is not None
    )


def email_in_use(session: Session, email: str) -> bool:
    """`email` must already be normalised (trimmed, lowercased), as stored."""
    return session.scalar(select(Employee.id).where(Employee.email == email)) is not None


# The only columns a list can be sorted by: sort fields never become SQL text.
SORT_COLUMNS: Mapping[str, QueryableAttribute[object]] = {
    "last_name": Employee.last_name,
    "first_name": Employee.first_name,
    "employee_code": Employee.employee_code,
    "hire_date": Employee.hire_date,
    "country": Employee.country_code,
    "level": Employee.level,
    "current_base": Employee.current_base_minor,
    "current_total": Employee.current_total_minor,
}
SALARY_SORT_FIELDS = frozenset({"current_base", "current_total"})


@dataclass(frozen=True, slots=True)
class SortKey:
    field: str  # a key of SORT_COLUMNS
    descending: bool = False


AMOUNT_COLUMNS: Mapping[Comp, QueryableAttribute[int]] = {
    Comp.BASE: Employee.current_base_minor,
    Comp.TOTAL: Employee.current_total_minor,
}


@dataclass(frozen=True, slots=True)
class Bounds:
    """Inclusive bounds in minor units of one currency; None means unbounded."""

    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True, slots=True)
class SalaryRange:
    """A salary range on base or total.

    `bounds` is one pair for rows the other filters keep to one currency, or one pair per
    currency (a USD range converted to each currency); a currency without bounds never matches.
    """

    comp: Comp
    bounds: Bounds | Mapping[str, Bounds]


@dataclass(frozen=True, slots=True)
class EmployeeFilter:
    """Which employees a list shows. An empty sequence means no condition on that field."""

    search: str | None = None  # already folded (domain/search.py)
    countries: Sequence[str] = ()
    department_ids: Sequence[int] = ()
    job_role_ids: Sequence[int] = ()
    levels: Sequence[Level] = ()
    employment_types: Sequence[EmploymentType] = ()
    statuses: Sequence[EmployeeStatus] = ()
    currencies: Sequence[str] = ()
    salary: SalaryRange | None = None


def page(
    session: Session,
    where: EmployeeFilter,
    *,
    order: Sequence[SortKey],
    offset: int,
    limit: int,
) -> Sequence[Employee]:
    """One page of matching employees with role and department loaded (one query).

    Sorted by `order`, then by id, so every page boundary is stable.
    """
    order_by = [
        SORT_COLUMNS[key.field].desc() if key.descending else SORT_COLUMNS[key.field].asc()
        for key in order
    ]
    query = (
        _matching(select(Employee), where)
        .options(contains_eager(Employee.job_role).contains_eager(JobRole.department))
        .join(JobRole.department)
        .order_by(*order_by, Employee.id)
        .offset(offset)
        .limit(limit)
    )
    return session.scalars(query).all()


def count(session: Session, where: EmployeeFilter) -> int:
    return session.scalar(_matching(select(func.count(Employee.id)), where)) or 0


def _matching[*Row](query: Select[*Row], where: EmployeeFilter) -> Select[*Row]:
    return query.select_from(Employee).join(Employee.job_role).where(*_conditions(where))


def _conditions(where: EmployeeFilter) -> list[ColumnElement[bool]]:
    candidates = [
        _any_of(Employee.country_code, where.countries),
        _any_of(JobRole.department_id, where.department_ids),
        _any_of(Employee.job_role_id, where.job_role_ids),
        _any_of(Employee.level, where.levels),
        _any_of(Employee.employment_type, where.employment_types),
        _any_of(Employee.status, where.statuses),
        _any_of(Employee.currency, where.currencies),
    ]
    if where.search:
        # LIKE '%term%' with % and _ in the term escaped, so they match themselves.
        candidates.append(Employee.search_text.contains(where.search, autoescape=True))
    if where.salary is not None:
        candidates += _salary_conditions(where.salary)
    return [condition for condition in candidates if condition is not None]


def _salary_conditions(salary: SalaryRange) -> list[ColumnElement[bool]]:
    column = AMOUNT_COLUMNS[salary.comp]
    if isinstance(salary.bounds, Bounds):
        return _within(column, salary.bounds)
    per_currency = [
        and_(Employee.currency == currency, *_within(column, bounds))
        for currency, bounds in salary.bounds.items()
    ]
    return [or_(false(), *per_currency)]


def _within(column: QueryableAttribute[int], bounds: Bounds) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if bounds.minimum is not None:
        conditions.append(column >= bounds.minimum)
    if bounds.maximum is not None:
        conditions.append(column <= bounds.maximum)
    return conditions


def _any_of[T](column: QueryableAttribute[T], values: Sequence[T]) -> ColumnElement[bool] | None:
    """`column IN (values)`, or no condition when no value is asked for."""
    return column.in_(values) if values else None
