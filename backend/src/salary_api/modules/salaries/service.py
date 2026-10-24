"""Salary history: the only writer of an employee's current salary (ADR 0006).

`record_hire` joins the caller's transaction; `record_salary_change` is a use case of its own
and commits.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from itertools import count
from typing import Any

from sqlalchemy.orm import Session

from salary_api.core.errors import FieldError, Forbidden, InvalidState, ValidationFailed
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import Money
from salary_api.domain.compensation import total_compensation
from salary_api.domain.enums import EmployeeStatus, Level, SalaryReason
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.salary_change import base_change_pct, is_promotion
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import locking
from salary_api.modules.employees import repository as employees
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference import repository as reference
from salary_api.modules.reference.models import Country, JobRole
from salary_api.modules.reference.schemas import JobRoleRef
from salary_api.modules.salaries import repository
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.salaries.schemas import (
    ChangedBy,
    Component,
    ComponentIn,
    SalaryChange,
    SalaryChangeRequest,
    SalaryHistory,
    SalaryHistoryRecord,
)


@dataclass(frozen=True, slots=True)
class Pay:
    """An annual base and its components, all in the base's currency (ADR 0010)."""

    base: DomainMoney
    components: Sequence[ComponentIn]

    @property
    def total(self) -> DomainMoney:
        """Base + every allowance and bonus target."""
        currency = self.base.currency
        return total_compensation(
            self.base, (DomainMoney(c.amount_minor, currency) for c in self.components)
        )


def record_hire(
    session: Session, employee: Employee, pay: Pay, *, note: str | None, changed_by: int
) -> SalaryRecord:
    """Append the HIRE record of a new (flushed) employee and make it the current salary."""
    record = _new_record(
        employee.id,
        pay,
        effective_date=employee.hire_date,
        reason=SalaryReason.HIRE,
        job_role_id=employee.job_role_id,
        level=employee.level,
        note=note,
        changed_by=changed_by,
    )
    repository.add_record(session, record)
    _make_current(employee, record)
    return record


@dataclass(frozen=True, slots=True)
class BulkHire:
    """The first salary of an employee inserted in bulk, with their role and level."""

    employee_id: int
    job_role_id: int
    level: Level
    effective_date: date
    pay: Pay


def record_hires_in_bulk(session: Session, hires: Sequence[BulkHire], *, changed_by: int) -> None:
    """Append the HIRE record of each new (inserted) employee and make it their current
    salary, with bulk inserts. Joins the caller's transaction.

    Record ids are allocated here, one more than the highest in use, so no RETURNING is
    needed; the caller's transaction holds the write lock (BEGIN IMMEDIATE on SQLite).
    """
    now = utc_now()
    records: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    current: dict[int, int] = {}
    for record_id, hire in zip(count(repository.highest_record_id(session) + 1), hires):
        records.append(
            {
                "id": record_id,
                "employee_id": hire.employee_id,
                "effective_date": hire.effective_date,
                "currency": hire.pay.base.currency,
                "base_minor": hire.pay.base.amount_minor,
                "total_minor": hire.pay.total.amount_minor,
                "job_role_id": hire.job_role_id,
                "level": hire.level,
                "reason": SalaryReason.HIRE,
                "note": None,
                "changed_by": changed_by,
                "created_at": now,
            }
        )
        components += [
            {
                "salary_record_id": record_id,
                "type": c.type,
                "name": c.name,
                "amount_minor": c.amount_minor,
            }
            for c in hire.pay.components
        ]
        current[hire.employee_id] = record_id
    repository.insert_records(session, records)
    if components:
        repository.insert_components(session, components)
    employees.set_current_salary_records(session, current)


def record_salary_change(
    session: Session, principal: Principal, employee_id: int, request: SalaryChangeRequest
) -> SalaryChange:
    """Append a salary record and make it the current salary, in one transaction."""
    employee = locking.get_version(session, employee_id, request.version)
    if employee.status != EmployeeStatus.ACTIVE:
        raise InvalidState(f"Employee {employee_id} is terminated: reactivate them first.")
    previous = repository.latest_record(session, employee_id)
    role = _job_role(session, employee, request.job_role_id)
    level = request.level or employee.level
    country = reference.get_country(session, request.country_code or employee.country_code)
    errors = _broken_rules(request, employee, previous, _Target(role, level, country))
    if errors or role is None or country is None:
        raise ValidationFailed(errors)
    # Every salary is in its country's currency (docs/README.md v1 scope).
    pay = Pay(DomainMoney(request.base_minor, country.default_currency), request.components)
    record = _new_record(
        employee.id,
        pay,
        effective_date=request.effective_date,
        reason=request.reason,
        job_role_id=role.id,
        level=level,
        note=request.note,
        changed_by=principal.user_id,
    )
    diff: dict[str, Any] = {
        "reason": request.reason,
        "effective_date": request.effective_date.isoformat(),
        "base_minor": [employee.current_base_minor, record.base_minor],
    }
    if role.id != employee.job_role_id:
        diff["job_role_id"] = [employee.job_role_id, role.id]
    if level != employee.level:
        diff["level"] = [employee.level, level]
    if country.code != employee.country_code:
        diff["country_code"] = [employee.country_code, country.code]
    if record.currency != employee.currency:
        diff["currency"] = [employee.currency, record.currency]
    repository.add_record(session, record)
    employee.job_role = role
    employee.level = level
    employee.country_code = country.code
    _make_current(employee, record)
    employee.version += 1
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.SALARY_CHANGE,
        entity="employee",
        entity_id=employee_id,
        diff={"salary_record_id": record.id, **diff},
    )
    locking.commit_versioned(session, employee_id)
    return SalaryChange(record=_history_record(record, previous), employee_version=employee.version)


def salary_history(session: Session, principal: Principal, employee_id: int) -> SalaryHistory:
    """Every salary record, oldest first. Individual pay, so SALARY_READ only (docs/08 4.1)."""
    if not principal.has(Permission.SALARY_READ):
        raise Forbidden("Salary history requires SALARY_READ.")
    locking.get(session, employee_id)  # NotFound for an unknown employee
    records = repository.history(session, employee_id)
    return SalaryHistory(
        employee_id=employee_id,
        records=[
            _history_record(record, previous)
            for previous, record in zip([None, *records], records, strict=False)
        ],
    )


@dataclass(frozen=True, slots=True)
class _Target:
    """The employee's role, level and country after the change (None: unknown id or code)."""

    role: JobRole | None
    level: Level
    country: Country | None


def _job_role(session: Session, employee: Employee, job_role_id: int | None) -> JobRole | None:
    """The role after the change: the current one unless another is asked for."""
    if job_role_id is None or job_role_id == employee.job_role_id:
        return employee.job_role
    return reference.get_job_role(session, job_role_id)


def _broken_rules(
    request: SalaryChangeRequest,
    employee: Employee,
    latest: SalaryRecord | None,
    target: "_Target",
) -> list[FieldError]:
    """Every rule of docs/07 section 6.7 the change breaks, as field errors."""
    errors: list[FieldError] = []
    if (date_error := _effective_date_error(request.effective_date, employee, latest)) is not None:
        errors.append(date_error)
    errors += _country_errors(request, employee, target.country)
    role, level = target.role, target.level
    if role is None:
        message = f"Unknown job role {request.job_role_id}."
        errors.append({"loc": ["body", "job_role_id"], "code": "not_found", "message": message})
    elif request.reason == SalaryReason.PROMOTION and not is_promotion(
        old_level=employee.level,
        new_level=level,
        old_role_id=employee.job_role_id,
        new_role_id=role.id,
    ):
        message = "A promotion needs a higher level or a different job role."
        errors.append({"loc": ["body", "reason"], "code": "not_a_promotion", "message": message})
    return errors


def _country_errors(
    request: SalaryChangeRequest, employee: Employee, country: Country | None
) -> list[FieldError]:
    """A relocation goes to a known, active country; the currency is always the country's."""
    if country is None:
        message = f"Unknown country {request.country_code}."
        return [{"loc": ["body", "country_code"], "code": "not_found", "message": message}]
    errors: list[FieldError] = []
    if country.code != employee.country_code and not country.is_active:
        message = f"{country.name} is not an active country."
        errors.append({"loc": ["body", "country_code"], "code": "inactive", "message": message})
    if request.currency not in (None, country.default_currency):
        message = f"Salaries in {country.name} are paid in {country.default_currency}."
        errors.append(
            {"loc": ["body", "currency"], "code": "currency_mismatch", "message": message}
        )
    return errors


def _effective_date_error(
    effective_date: date, employee: Employee, latest: SalaryRecord | None
) -> FieldError | None:
    """No future-dated changes, nothing before the hire date or the latest record (ADR 0006),
    so the latest record is always the current one."""
    if effective_date > utc_now().date():
        code, message = "future_date", "A salary change cannot take effect in the future."
    elif effective_date < employee.hire_date:
        code, message = "before_hire_date", f"The employee was hired on {employee.hire_date}."
    elif latest is not None and effective_date < latest.effective_date:
        code = "before_latest_record"
        message = f"The latest salary record is effective {latest.effective_date}."
    else:
        return None
    return {"loc": ["body", "effective_date"], "code": code, "message": message}


def _new_record(  # noqa: PLR0913  (one keyword per snapshot column)
    employee_id: int,
    pay: Pay,
    *,
    effective_date: date,
    reason: SalaryReason,
    job_role_id: int,
    level: Level,
    note: str | None,
    changed_by: int,
) -> SalaryRecord:
    return SalaryRecord(
        employee_id=employee_id,
        effective_date=effective_date,
        currency=pay.base.currency,
        base_minor=pay.base.amount_minor,
        total_minor=pay.total.amount_minor,
        job_role_id=job_role_id,
        level=level,
        reason=reason,
        note=note,
        changed_by=changed_by,
        components=[
            SalaryComponent(type=c.type, name=c.name, amount_minor=c.amount_minor)
            for c in pay.components
        ],
    )


def _history_record(record: SalaryRecord, previous: SalaryRecord | None) -> SalaryHistoryRecord:
    """A record as history shows it, with the base change from `previous`."""
    base = DomainMoney(record.base_minor, record.currency)
    pct = (
        None
        if previous is None
        else base_change_pct(DomainMoney(previous.base_minor, previous.currency), base)
    )
    user = record.changed_by_user
    return SalaryHistoryRecord(
        id=record.id,
        effective_date=record.effective_date,
        reason=record.reason,
        job_role=JobRoleRef(id=record.job_role.id, title=record.job_role.title),
        level=record.level,
        base=_money(record.base_minor, record.currency),
        total=_money(record.total_minor, record.currency),
        components=[
            Component(type=c.type, name=c.name, amount=_money(c.amount_minor, record.currency))
            for c in record.components
        ],
        base_change_pct=None if pct is None else str(pct),
        changed_by=None if user is None else ChangedBy(id=user.id, full_name=user.full_name),
        note=record.note,
        created_at=record.created_at,
    )


def _money(amount_minor: int, currency: str) -> Money:
    return Money(amount_minor=amount_minor, currency=currency)


def _make_current(employee: Employee, record: SalaryRecord) -> None:
    """Copy the record onto the employee's current-salary columns (docs/06 section 6.2)."""
    # The relationship, not only the id, so a session that loaded the old record sees the new.
    employee.current_salary_record = record
    employee.currency = record.currency
    employee.current_base_minor = record.base_minor
    employee.current_total_minor = record.total_minor
