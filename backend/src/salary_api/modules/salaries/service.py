"""Salary history: the only writer of an employee's current salary (ADR 0006).

`record_hire` joins the caller's transaction; `record_salary_change` is a use case of its own
and commits.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal
from salary_api.core.schemas import Money
from salary_api.domain.compensation import total_compensation
from salary_api.domain.enums import Level, SalaryReason
from salary_api.domain.money import Money as DomainMoney
from salary_api.domain.salary_change import base_change_pct
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import locking
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.schemas import JobRoleRef
from salary_api.modules.salaries import repository
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.salaries.schemas import (
    ChangedBy,
    Component,
    ComponentIn,
    SalaryChange,
    SalaryChangeRequest,
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


def record_salary_change(
    session: Session, principal: Principal, employee_id: int, request: SalaryChangeRequest
) -> SalaryChange:
    """Append a salary record and make it the current salary, in one transaction."""
    employee = locking.get_version(session, employee_id, request.version)
    previous = repository.latest_record(session, employee_id)
    pay = Pay(DomainMoney(request.base_minor, employee.currency), request.components)
    record = _new_record(
        employee.id,
        pay,
        effective_date=request.effective_date,
        reason=request.reason,
        job_role_id=employee.job_role_id,
        level=employee.level,
        note=request.note,
        changed_by=principal.user_id,
    )
    diff: dict[str, Any] = {
        "reason": request.reason,
        "effective_date": request.effective_date.isoformat(),
        "base_minor": [employee.current_base_minor, record.base_minor],
    }
    repository.add_record(session, record)
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
    employee.current_salary_record_id = record.id
    employee.currency = record.currency
    employee.current_base_minor = record.base_minor
    employee.current_total_minor = record.total_minor
