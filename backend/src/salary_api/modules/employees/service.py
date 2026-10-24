"""Employee use cases. Each public function is one transaction (it commits).

Masking lives here, not in the router: the Ask tools and exports call these functions
directly with the caller's Principal (docs/08-security-rbac.md section 3.3).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from salary_api.core.errors import (
    Duplicate,
    FieldError,
    Forbidden,
    InvalidState,
    ValidationFailed,
)
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import Comp, Money, SalaryBasis
from salary_api.domain.currency import SUPPORTED_CURRENCIES
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.domain.money import (
    FxRate,
    FxRateMissingError,
    max_local_amount,
    min_local_amount,
    usd_sort_key,
)
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.search import employee_search_text, fold
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import locking, repository
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.schemas import (
    CurrentSalary,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeFilterQuery,
    EmployeeListItem,
    EmployeeListQuery,
    EmployeePage,
    EmployeeUpdate,
    ReactivateRequest,
    TerminateRequest,
)
from salary_api.modules.reference import repository as reference
from salary_api.modules.reference import service as reference_service
from salary_api.modules.reference.models import Country
from salary_api.modules.reference.schemas import Department, JobRoleRef
from salary_api.modules.salaries import service as salaries
from salary_api.modules.salaries.models import SalaryRecord
from salary_api.modules.salaries.schemas import Component

ENTITY = "employee"  # audit events name the entity they change
CODE_PREFIX = "ACME-"
LAST_CODE_NUMBER = 999_999  # codes have six digits
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


@dataclass(frozen=True, slots=True)
class NewHire:
    """A new employee and their first salary, already validated (the bulk import's rows)."""

    employee_code: str
    first_name: str
    last_name: str
    email: str  # trimmed and lowercased
    job_role_id: int
    level: Level
    employment_type: EmploymentType
    country_code: str
    hire_date: date
    salary_effective_date: date  # of the HIRE record; on or after the hire date
    pay: salaries.Pay  # in the country's currency


def add_hires_in_bulk(session: Session, hires: Sequence[NewHire], *, changed_by: int) -> None:
    """Insert new employees, each with a HIRE salary record, with bulk inserts. Joins the
    caller's transaction (no commit, no audit event: the caller writes one for the batch).

    The same rules as create_employee: search text, and the current salary copied from the
    HIRE record. Ids are allocated here, so no RETURNING is needed; the caller's
    transaction holds the write lock (BEGIN IMMEDIATE on SQLite).
    """
    now = utc_now()
    first_id = repository.highest_id(session) + 1
    ids = range(first_id, first_id + len(hires))
    repository.insert_many(
        session,
        [
            {
                "id": employee_id,
                "employee_code": hire.employee_code,
                "first_name": hire.first_name,
                "last_name": hire.last_name,
                "email": hire.email,
                "search_text": employee_search_text(
                    hire.first_name, hire.last_name, hire.employee_code, hire.email
                ),
                "job_role_id": hire.job_role_id,
                "level": hire.level,
                "employment_type": hire.employment_type,
                "country_code": hire.country_code,
                "status": EmployeeStatus.ACTIVE,
                "hire_date": hire.hire_date,
                "termination_date": None,
                "currency": hire.pay.base.currency,
                "current_base_minor": hire.pay.base.amount_minor,
                "current_total_minor": hire.pay.total.amount_minor,
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
            for employee_id, hire in zip(ids, hires, strict=True)
        ],
    )
    salaries.record_hires_in_bulk(
        session,
        [
            salaries.BulkHire(
                employee_id=employee_id,
                job_role_id=hire.job_role_id,
                level=hire.level,
                effective_date=hire.salary_effective_date,
                pay=hire.pay,
            )
            for employee_id, hire in zip(ids, hires, strict=True)
        ],
        changed_by=changed_by,
    )


def get_employee(session: Session, principal: Principal, employee_id: int) -> EmployeeDetail:
    return _detail(_get(session, employee_id), salary_visible=can_see_salaries(principal))


def update_employee(
    session: Session, principal: Principal, employee_id: int, request: EmployeeUpdate
) -> EmployeeDetail:
    """Change profile fields of the version the client read; the version goes up by one."""
    employee = locking.get_version(session, employee_id, request.version)
    if request.email is not None and repository.email_in_use(
        session, request.email, other_than=employee_id
    ):
        raise Duplicate(f"The email {request.email} is already in use by another employee.")
    requested = request.model_dump(exclude_unset=True, exclude={"version"})
    changes = {
        field: [getattr(employee, field), value]
        for field, value in requested.items()
        if getattr(employee, field) != value
    }
    if not changes:  # nothing to write, so no new version and no audit event
        return _detail(employee, salary_visible=can_see_salaries(principal))
    for field, (_old, new) in changes.items():
        setattr(employee, field, new)
    employee.search_text = employee_search_text(
        employee.first_name, employee.last_name, employee.employee_code, employee.email
    )
    return _commit_change(session, principal, employee, AuditAction.EMPLOYEE_UPDATE, changes)


def terminate_employee(
    session: Session, principal: Principal, employee_id: int, request: TerminateRequest
) -> EmployeeDetail:
    """Soft delete: the employee and their salary history stay (ADR 0013)."""
    employee = locking.get_version(session, employee_id, request.version)
    _require_status(employee, EmployeeStatus.ACTIVE)
    termination_date = request.termination_date or _today()
    if termination_date < employee.hire_date:
        message = f"The termination date cannot be before the hire date ({employee.hire_date})."
        raise ValidationFailed([_field_error(("termination_date",), "before_hire_date", message)])
    diff: dict[str, Any] = {
        "status": [employee.status, EmployeeStatus.TERMINATED],
        "termination_date": [None, termination_date.isoformat()],
    }
    if request.note:
        diff["note"] = request.note
    employee.status = EmployeeStatus.TERMINATED
    employee.termination_date = termination_date
    return _commit_change(session, principal, employee, AuditAction.EMPLOYEE_TERMINATE, diff)


def reactivate_employee(
    session: Session, principal: Principal, employee_id: int, request: ReactivateRequest
) -> EmployeeDetail:
    employee = locking.get_version(session, employee_id, request.version)
    _require_status(employee, EmployeeStatus.TERMINATED)
    termination_date = employee.termination_date
    diff = {
        "status": [employee.status, EmployeeStatus.ACTIVE],
        "termination_date": [termination_date.isoformat() if termination_date else None, None],
    }
    employee.status = EmployeeStatus.ACTIVE
    employee.termination_date = None
    return _commit_change(session, principal, employee, AuditAction.EMPLOYEE_REACTIVATE, diff)


def _commit_change(
    session: Session,
    principal: Principal,
    employee: Employee,
    action: AuditAction,
    diff: Mapping[str, Any],
) -> EmployeeDetail:
    """Bump the version, audit the change and commit both together."""
    employee.version += 1
    record_event(
        session,
        actor_id=principal.user_id,
        action=action,
        entity=ENTITY,
        entity_id=employee.id,
        diff=diff,
    )
    locking.commit_versioned(session, employee.id)
    return get_employee(session, principal, employee.id)


def _require_status(employee: Employee, status: EmployeeStatus) -> None:
    if employee.status != status:
        raise InvalidState(f"Employee {employee.id} is {employee.status.lower()}.")


def _get(session: Session, employee_id: int) -> Employee:
    return locking.get(session, employee_id)


def list_employees(
    session: Session, principal: Principal, query: EmployeeListQuery
) -> EmployeePage:
    """One page of employees, `ACTIVE` ones by default, sorted by name.

    Salary filters and sorts need SALARY_READ (Forbidden otherwise).
    """
    where, order = _filter_and_order(session, principal, query)
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


def matching_employees(
    session: Session, principal: Principal, query: EmployeeFilterQuery
) -> Sequence[Employee]:
    """Every employee the query matches, in its order, without paging (the export).

    The same filters, sort and refusals as list_employees: what you see is what you export.
    """
    where, order = _filter_and_order(session, principal, query)
    return repository.all_matching(session, where, order=order)


def _filter_and_order(
    session: Session, principal: Principal, query: EmployeeFilterQuery
) -> tuple[repository.EmployeeFilter, list[repository.SortKey]]:
    """The WHERE and ORDER BY of a query, once the caller may filter and sort that way."""
    order = _sort_keys(query.sort)
    _refuse_salary_query_without_salary_read(principal, query, order)
    _check_salary_comparison(query, order)
    usd_rates = _usd_rates_for(session, query, order)
    if usd_rates:
        order = _by_usd_value(order, usd_rates)
    where = repository.EmployeeFilter(
        search=fold(query.q) if query.q else None,
        countries=query.country,
        department_ids=query.department_id,
        job_role_ids=query.job_role_id,
        levels=query.level,
        employment_types=query.employment_type,
        statuses=query.status,
        currencies=query.currency,
        salary=_salary_range(query, usd_rates),
    )
    return where, order


def _salary_range(
    query: EmployeeFilterQuery, usd_rates: Mapping[str, FxRate]
) -> repository.SalaryRange | None:
    """The salary range in local minor units: as given, or converted from USD per currency."""
    minimum, maximum = query.salary_min, query.salary_max
    if minimum is None and maximum is None:
        return None
    comp = query.comp or Comp.BASE
    if query.salary_basis != SalaryBasis.USD:
        return repository.SalaryRange(comp, repository.Bounds(minimum, maximum))
    return repository.SalaryRange(
        comp,
        {
            currency: repository.Bounds(
                None if minimum is None else min_local_amount(minimum, rate),
                None if maximum is None else max_local_amount(maximum, rate),
            )
            for currency, rate in usd_rates.items()
        },
    )


def _by_usd_value(
    order: list[repository.SortKey], usd_rates: Mapping[str, FxRate]
) -> list[repository.SortKey]:
    """Salary sort keys that order by USD value, the others unchanged."""
    usd = {currency: usd_sort_key(rate) for currency, rate in usd_rates.items()}
    return [
        replace(key, usd=usd) if key.field in repository.SALARY_SORT_FIELDS else key
        for key in order
    ]


def _usd_rates_for(
    session: Session, query: EmployeeFilterQuery, order: list[repository.SortKey]
) -> dict[str, FxRate]:
    """When salaries are compared in USD: the rate of every currency the list can hold (the
    `currency` filter, else every supported currency). A missing rate is a configuration
    error. Without a salary range or sort nothing is compared, so no rate is needed."""
    compared = query.salary_min is not None or query.salary_max is not None or _salary_sorted(order)
    if query.salary_basis != SalaryBasis.USD or not compared:
        return {}
    rates = reference_service.usd_rates(session)
    currencies = [
        c for c in query.currency or sorted(SUPPORTED_CURRENCIES) if c in SUPPORTED_CURRENCIES
    ]
    missing = [currency for currency in currencies if currency not in rates]
    if missing:
        raise FxRateMissingError(missing[0])
    return {currency: rates[currency] for currency in currencies}


def _refuse_salary_query_without_salary_read(
    principal: Principal, query: EmployeeFilterQuery, order: list[repository.SortKey]
) -> None:
    """Without SALARY_READ, narrowing a salary range could reveal one person's pay (docs/08 4.1)."""
    salary_filter = any(
        value is not None
        for value in (query.salary_min, query.salary_max, query.salary_basis, query.comp)
    )
    if (salary_filter or _salary_sorted(order)) and not can_see_salaries(principal):
        raise Forbidden("Filtering or sorting by salary requires SALARY_READ.")


def _check_salary_comparison(query: EmployeeFilterQuery, order: list[repository.SortKey]) -> None:
    """Salaries are compared in one currency or in USD, never as raw minor units of two
    currencies (¥6,000,000 is not more than €60,000.00). Every salary is in its country's
    currency, so one country also means one currency."""
    errors: list[FieldError] = []
    ranged = [
        field
        for field, value in (("salary_min", query.salary_min), ("salary_max", query.salary_max))
        if value is not None
    ]
    minimum, maximum = query.salary_min, query.salary_max
    if minimum is not None and maximum is not None and minimum > maximum:
        message = "salary_min is above salary_max."
        errors.append({"loc": ["query", "salary_min"], "code": "invalid_range", "message": message})
    one_currency = len(query.currency) == 1 or len(query.country) == 1
    if query.salary_basis != SalaryBasis.USD and not one_currency:
        message = (
            "Salaries in different currencies cannot be compared: choose one currency "
            "(or one country), or use salary_basis=usd."
        )
        for field in ranged[:1] + (["sort"] if _salary_sorted(order) else []):
            errors.append(
                {"loc": ["query", field], "code": "currency_required", "message": message}
            )
    if errors:
        raise ValidationFailed(errors)


def _salary_sorted(order: list[repository.SortKey]) -> bool:
    return any(key.field in repository.SALARY_SORT_FIELDS for key in order)


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
        "version": employee.version if salary_visible else None,
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
    else:
        if not country.is_active:
            message = f"{country.name} is not an active country."
            errors.append(_field_error(("country_code",), "inactive", message))
        if request.salary.currency not in (None, country.default_currency):
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
    if number > LAST_CODE_NUMBER:
        raise InvalidState(
            f"No employee code can follow {highest}: give a free employee_code (ACME-######)."
        )
    return f"{CODE_PREFIX}{number:06d}"


def _field_error(loc: tuple[str, ...], code: str, message: str) -> FieldError:
    return {"loc": ["body", *loc], "code": code, "message": message}
