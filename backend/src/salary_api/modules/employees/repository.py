from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import QueryableAttribute, Session, contains_eager, joinedload

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


@dataclass(frozen=True, slots=True)
class EmployeeFilter:
    """Which employees a list shows. An empty sequence means no condition on that field."""

    countries: Sequence[str] = ()
    department_ids: Sequence[int] = ()
    job_role_ids: Sequence[int] = ()
    levels: Sequence[Level] = ()
    employment_types: Sequence[EmploymentType] = ()
    statuses: Sequence[EmployeeStatus] = ()
    currencies: Sequence[str] = ()


def page(session: Session, where: EmployeeFilter, *, offset: int, limit: int) -> Sequence[Employee]:
    """One page of matching employees with role and department loaded (one query)."""
    query = (
        _matching(select(Employee), where)
        .options(contains_eager(Employee.job_role).contains_eager(JobRole.department))
        .join(JobRole.department)
        .order_by(Employee.last_name, Employee.first_name, Employee.id)
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
    return [condition for condition in candidates if condition is not None]


def _any_of[T](column: QueryableAttribute[T], values: Sequence[T]) -> ColumnElement[bool] | None:
    """`column IN (values)`, or no condition when no value is asked for."""
    return column.in_(values) if values else None
