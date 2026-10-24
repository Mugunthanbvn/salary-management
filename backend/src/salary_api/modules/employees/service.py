"""Employee use cases. Each public function is one transaction (it commits).

Masking lives here, not in the router: the Ask tools and exports call these functions
directly with the caller's Principal (docs/08-security-rbac.md section 3.3).
"""

from sqlalchemy.orm import Session

from salary_api.core.errors import Duplicate, FieldError, NotFound, ValidationFailed
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import Money
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.search import employee_search_text
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import repository
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.schemas import (
    CurrentSalary,
    EmployeeCreate,
    EmployeeDetail,
)
from salary_api.modules.reference import repository as reference
from salary_api.modules.reference.schemas import Department, JobRoleRef
from salary_api.modules.salaries import service as salaries
from salary_api.modules.salaries.models import SalaryRecord
from salary_api.modules.salaries.schemas import Component

ENTITY = "employee"  # audit events name the entity they change
CODE_PREFIX = "ACME-"


def create_employee(
    session: Session, principal: Principal, request: EmployeeCreate
) -> EmployeeDetail:
    """Create the employee and its HIRE salary record together (docs/06 section 6.1)."""
    country = reference.get_country(session, request.country_code)
    if country is None:
        raise ValidationFailed(
            [_field_error("country_code", "not_found", f"Unknown country {request.country_code}.")]
        )
    pay = salaries.Pay(
        base=DomainMoney(request.salary.base_minor, country.default_currency),
        components=request.salary.components,
    )
    code = request.employee_code or _next_employee_code(session)
    _refuse_duplicates(session, employee_code=code, email=request.email)
    employee = Employee(
        employee_code=code,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        search_text=employee_search_text(
            request.first_name, request.last_name, code, request.email
        ),
        job_role_id=request.job_role_id,
        level=request.level,
        employment_type=request.employment_type,
        country_code=country.code,
        hire_date=request.hire_date,
        # The first salary, until its HIRE record exists (the record is written next).
        currency=pay.base.currency,
        current_base_minor=pay.base.amount_minor,
        current_total_minor=pay.total.amount_minor,
    )
    repository.add(session, employee)
    record = salaries.record_hire(
        session, employee, pay, note=request.salary.note, changed_by=principal.user_id
    )
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.EMPLOYEE_CREATE,
        entity=ENTITY,
        entity_id=employee.id,
        # The created fields; the salary only as its record id (docs/08 section 6).
        diff={
            "employee_code": employee.employee_code,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "job_role_id": employee.job_role_id,
            "level": employee.level,
            "employment_type": employee.employment_type,
            "country_code": employee.country_code,
            "hire_date": employee.hire_date.isoformat(),
            "salary_record_id": record.id,
        },
    )
    session.commit()
    return get_employee(session, principal, employee.id)


def get_employee(session: Session, principal: Principal, employee_id: int) -> EmployeeDetail:
    employee = repository.get_detail(session, employee_id)
    if employee is None:
        raise NotFound(f"Employee {employee_id} was not found.")
    return _detail(employee, salary_visible=principal.has(Permission.SALARY_READ))


def _detail(employee: Employee, *, salary_visible: bool) -> EmployeeDetail:
    role = employee.job_role
    record = employee.current_salary_record
    return EmployeeDetail(
        id=employee.id,
        employee_code=employee.employee_code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        job_role=JobRoleRef(id=role.id, title=role.title),
        department=Department(id=role.department.id, name=role.department.name),
        level=employee.level,
        employment_type=employee.employment_type,
        country_code=employee.country_code,
        status=employee.status,
        hire_date=employee.hire_date,
        termination_date=employee.termination_date,
        current_base=Money(amount_minor=employee.current_base_minor, currency=employee.currency),
        current_total=Money(amount_minor=employee.current_total_minor, currency=employee.currency),
        current_salary=_current_salary(record) if record else None,
        salary_masked=not salary_visible,
        version=employee.version,
    )


def _current_salary(record: SalaryRecord) -> CurrentSalary:
    return CurrentSalary(
        id=record.id,
        effective_date=record.effective_date,
        reason=record.reason,
        components=[
            Component(
                type=c.type,
                name=c.name,
                amount=Money(amount_minor=c.amount_minor, currency=record.currency),
            )
            for c in record.components
        ],
    )


def _refuse_duplicates(session: Session, *, employee_code: str, email: str) -> None:
    if repository.code_in_use(session, employee_code):
        raise Duplicate(f"The employee_code {employee_code} is already in use.")
    if repository.email_in_use(session, email):
        raise Duplicate(f"The email {email} is already in use by another employee.")


def _next_employee_code(session: Session) -> str:
    """`ACME-` and six digits: one more than the highest code in use."""
    highest = repository.highest_employee_code(session)
    number = int(highest.removeprefix(CODE_PREFIX)) + 1 if highest else 1
    return f"{CODE_PREFIX}{number:06d}"


def _field_error(field: str, code: str, message: str) -> FieldError:
    return {"loc": ["body", field], "code": code, "message": message}
