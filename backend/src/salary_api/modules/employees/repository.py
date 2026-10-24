from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

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
