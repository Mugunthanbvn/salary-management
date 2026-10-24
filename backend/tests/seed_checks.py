"""Read-backs shared by the seed tests: the golden checksum and the inputs of pay equity."""

import hashlib
from datetime import date

from sqlalchemy import Connection, and_, select
from sqlalchemy.orm import Session

from salary_api.domain.enums import EmployeeStatus
from salary_api.domain.money import Money
from salary_api.domain.pay_equity import EmployeePay
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import JobRole, PayBand

SEED_TODAY = date(2026, 10, 1)


def employee_checksum(connection: Connection) -> str:
    """sha256 over the sorted (employee_code, country, job_role, level, employment_type,
    current_base_minor, current_total_minor) tuples, one `|`-joined line each
    (docs/12-seed-data.md section 12)."""
    rows = connection.execute(
        select(
            Employee.employee_code,
            Employee.country_code,
            JobRole.title,
            Employee.level,
            Employee.employment_type,
            Employee.current_base_minor,
            Employee.current_total_minor,
        ).join(JobRole, JobRole.id == Employee.job_role_id)
    ).all()
    lines = sorted("|".join(str(value) for value in row) for row in rows)
    return hashlib.sha256("".join(f"{line}\n" for line in lines).encode()).hexdigest()


def active_employee_pay(session: Session) -> list[tuple[Employee, EmployeePay]]:
    """Every active employee with what pay equity needs, their band mid from pay_bands."""
    band = and_(
        PayBand.job_role_id == Employee.job_role_id,
        PayBand.level == Employee.level,
        PayBand.country_code == Employee.country_code,
        PayBand.effective_from <= SEED_TODAY,
    )
    rows = session.execute(
        select(Employee, JobRole.department_id, PayBand.mid_minor)
        .join(JobRole, JobRole.id == Employee.job_role_id)
        .outerjoin(PayBand, band)
        .where(Employee.status == EmployeeStatus.ACTIVE)
    ).all()
    return [
        (
            employee,
            EmployeePay(
                department_id=department_id,
                job_role_id=employee.job_role_id,
                level=employee.level,
                country_code=employee.country_code,
                employment_type=employee.employment_type,
                base=Money(employee.current_base_minor, employee.currency),
                band_mid=None if mid is None else Money(mid, employee.currency),
            ),
        )
        for employee, department_id, mid in rows
    ]
