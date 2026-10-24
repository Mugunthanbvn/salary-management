"""Read-backs shared by the seed tests: the golden checksums and the inputs of pay equity."""

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from datetime import date

from sqlalchemy import Connection, and_, select
from sqlalchemy.orm import Session

from salary_api.domain.enums import EmployeeStatus
from salary_api.domain.money import Money
from salary_api.domain.pay_equity import EmployeePay
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import JobRole, PayBand
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord

SEED_TODAY = date(2026, 10, 1)


def employee_checksum(connection: Connection) -> str:
    """sha256 over the sorted (employee_code, country, job_role, level, employment_type,
    current_base_minor, current_total_minor, first_name, last_name, email, hire_date, status,
    termination_date) tuples, one `|`-joined line each (docs/12-seed-data.md section 12)."""
    rows = connection.execute(
        select(
            Employee.employee_code,
            Employee.country_code,
            JobRole.title,
            Employee.level,
            Employee.employment_type,
            Employee.current_base_minor,
            Employee.current_total_minor,
            Employee.first_name,
            Employee.last_name,
            Employee.email,
            Employee.hire_date,
            Employee.status,
            Employee.termination_date,
        ).join(JobRole, JobRole.id == Employee.job_role_id)
    ).all()
    return _sha256_of_sorted_lines("|".join(str(value) for value in row) for row in rows)


def history_checksum(connection: Connection) -> str:
    """sha256 over every salary record (employee_code, effective_date, reason, level,
    base_minor, total_minor), each followed by its components (type:name:amount_minor) in
    ID order, one line per record, sorted (docs/12-seed-data.md section 12)."""
    components: defaultdict[int, list[str]] = defaultdict(list)
    for record_id, kind, name, amount in connection.execute(
        select(
            SalaryComponent.salary_record_id,
            SalaryComponent.type,
            SalaryComponent.name,
            SalaryComponent.amount_minor,
        ).order_by(SalaryComponent.id)
    ):
        components[record_id].append(f"{kind}:{name}:{amount}")
    records = connection.execute(
        select(
            SalaryRecord.id,
            Employee.employee_code,
            SalaryRecord.effective_date,
            SalaryRecord.reason,
            SalaryRecord.level,
            SalaryRecord.base_minor,
            SalaryRecord.total_minor,
        ).join(Employee, Employee.id == SalaryRecord.employee_id)
    )
    return _sha256_of_sorted_lines(
        "|".join([*(str(value) for value in fields), ";".join(components[record_id])])
        for record_id, *fields in records
    )


def _sha256_of_sorted_lines(lines: Iterable[str]) -> str:
    text = "".join(f"{line}\n" for line in sorted(lines))
    return hashlib.sha256(text.encode()).hexdigest()


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
