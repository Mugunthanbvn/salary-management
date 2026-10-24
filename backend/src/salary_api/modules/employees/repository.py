from sqlalchemy import select
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
