"""Employee use cases. Each public function is one transaction (it commits).

Masking lives here, not in the router: the Ask tools and exports call these functions
directly with the caller's Principal (docs/08-security-rbac.md section 3.3).
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from salary_api.core.errors import Duplicate, FieldError, Forbidden, NotFound, ValidationFailed
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import Money
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.search import employee_search_text, fold
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import repository
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.schemas import (
    CurrentSalary,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListItem,
    EmployeeListQuery,
    EmployeePage,
)
from salary_api.modules.reference import repository as reference
from salary_api.modules.reference.models import Country
from salary_api.modules.reference.schemas import Department, JobRoleRef
from salary_api.modules.salaries import service as salaries
from salary_api.modules.salaries.models import SalaryRecord
from salary_api.modules.salaries.schemas import Component

ENTITY = "employee"  # audit events name the entity they change
CODE_PREFIX = "ACME-"
# After the requested sort fields; the repository ends every order with the id.
TIEBREAK = ("last_name", "first_name")


def can_see_salaries(principal: Principal) -> bool:
    """Whether the caller may see individual salaries. Without it, salaries are masked."""
    return principal.has(Permission.SALARY_READ)


def create_employee(
    session: Session, principal: Principal, request: EmployeeCreate
) -> EmployeeDetail:
    """Create the employee and its HIRE salary record together (docs/06 section 6.1)."""
    country = _check_new_employee(session, request)
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
    return _detail(employee, salary_visible=can_see_salaries(principal))


def list_employees(
    session: Session, principal: Principal, query: EmployeeListQuery
) -> EmployeePage:
    """One page of employees, `ACTIVE` ones by default, sorted by name.

    Salary filters and sorts need SALARY_READ (Forbidden otherwise).
    """
    order = _sort_keys(query.sort)
    _refuse_salary_query_without_salary_read(principal, query, order)
    where = repository.EmployeeFilter(
        search=fold(query.q) if query.q else None,
        countries=query.country,
        department_ids=query.department_id,
        job_role_ids=query.job_role_id,
        levels=query.level,
        employment_types=query.employment_type,
        statuses=query.status,
        currencies=query.currency,
    )
    employees = repository.page(
        session,
        where,
        order=order,
        offset=(query.page - 1) * query.page_size,
        limit=query.page_size,
    )
    salary_visible = can_see_salaries(principal)
    return EmployeePage(
        items=[
            EmployeeListItem(**_list_fields(employee, salary_visible=salary_visible))
            for employee in employees
        ],
        page=query.page,
        page_size=query.page_size,
        total=repository.count(session, where),
    )


def _refuse_salary_query_without_salary_read(
    principal: Principal, query: EmployeeListQuery, order: list[repository.SortKey]
) -> None:
    """Without SALARY_READ, narrowing a salary range could reveal one person's pay (docs/08 4.1)."""
    salary_filter = any(
        value is not None
        for value in (query.salary_min, query.salary_max, query.salary_basis, query.comp)
    )
    salary_sort = any(key.field in repository.SALARY_SORT_FIELDS for key in order)
    if (salary_filter or salary_sort) and not can_see_salaries(principal):
        raise Forbidden("Filtering or sorting by salary requires SALARY_READ.")


def _sort_keys(sort: str | None) -> list[repository.SortKey]:
    """The requested sort keys, then the tiebreak fields the request did not name."""
    requested: list[repository.SortKey] = []
    for token in sort.split(",") if sort is not None else []:
        field = token.removeprefix("-")
        if field not in repository.SORT_COLUMNS:
            allowed = ", ".join(repository.SORT_COLUMNS)
            raise ValidationFailed(
                [
                    {
                        "loc": ["query", "sort"],
                        "code": "unknown_sort_field",
                        "message": f"Cannot sort by {field!r}. Sort by: {allowed}.",
                    }
                ]
            )
        requested.append(repository.SortKey(field, descending=token.startswith("-")))
    named = {key.field for key in requested}
    return requested + [repository.SortKey(field) for field in TIEBREAK if field not in named]


def _detail(employee: Employee, *, salary_visible: bool) -> EmployeeDetail:
    record = employee.current_salary_record
    return EmployeeDetail(
        **_list_fields(employee, salary_visible=salary_visible),
        termination_date=employee.termination_date,
        current_salary=_current_salary(record) if record and salary_visible else None,
    )


def _list_fields(employee: Employee, *, salary_visible: bool) -> dict[str, Any]:
    """The fields of a list item, which the detail repeats."""
    role = employee.job_role
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "job_role": JobRoleRef(id=role.id, title=role.title),
        "department": Department(id=role.department.id, name=role.department.name),
        "level": employee.level,
        "employment_type": employee.employment_type,
        "country_code": employee.country_code,
        "status": employee.status,
        "hire_date": employee.hire_date,
        "current_base": _money(employee.current_base_minor, employee.currency, salary_visible),
        "current_total": _money(employee.current_total_minor, employee.currency, salary_visible),
        "salary_masked": not salary_visible,
        "version": employee.version,
    }


def _money(amount_minor: int, currency: str, visible: bool) -> Money | None:
    """An individual salary amount, or None for a caller without SALARY_READ."""
    return Money(amount_minor=amount_minor, currency=currency) if visible else None


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


def _check_new_employee(session: Session, request: EmployeeCreate) -> Country:
    """The employee's country, if every business rule holds; else one 422 listing each break."""
    errors: list[FieldError] = []
    if reference.get_job_role(session, request.job_role_id) is None:
        errors.append(
            _field_error(("job_role_id",), "not_found", f"Unknown job role {request.job_role_id}.")
        )
    country = reference.get_country(session, request.country_code)
    if country is None:
        message = f"Unknown country {request.country_code}."
        errors.append(_field_error(("country_code",), "not_found", message))
    elif not country.is_active:
        message = f"{country.name} is not an active country."
        errors.append(_field_error(("country_code",), "inactive", message))
    elif request.salary.currency not in (None, country.default_currency):
        message = f"Salaries in {country.name} are paid in {country.default_currency}."
        errors.append(_field_error(("salary", "currency"), "currency_mismatch", message))
    if request.hire_date > _today():
        message = "The hire date cannot be in the future."
        errors.append(_field_error(("hire_date",), "future_date", message))
    if errors or country is None:
        raise ValidationFailed(errors)
    return country


def _today() -> date:
    return utc_now().date()


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


def _field_error(loc: tuple[str, ...], code: str, message: str) -> FieldError:
    return {"loc": ["body", *loc], "code": code, "message": message}
