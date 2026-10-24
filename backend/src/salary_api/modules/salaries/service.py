"""Salary history: the only writer of an employee's current salary (ADR 0006).

Callers own the transaction: these functions add rows and never commit.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from salary_api.domain.compensation import total_compensation
from salary_api.domain.enums import SalaryReason
from salary_api.domain.money import Money as DomainMoney
from salary_api.modules.employees.models import Employee
from salary_api.modules.salaries import repository
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.salaries.schemas import ComponentIn


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
    record = SalaryRecord(
        employee_id=employee.id,
        effective_date=employee.hire_date,
        currency=pay.base.currency,
        base_minor=pay.base.amount_minor,
        total_minor=pay.total.amount_minor,
        job_role_id=employee.job_role_id,
        level=employee.level,
        reason=SalaryReason.HIRE,
        note=note,
        changed_by=changed_by,
        components=[
            SalaryComponent(type=c.type, name=c.name, amount_minor=c.amount_minor)
            for c in pay.components
        ],
    )
    repository.add_record(session, record)
    _make_current(employee, record)
    return record


def _make_current(employee: Employee, record: SalaryRecord) -> None:
    """Copy the record onto the employee's current-salary columns (docs/06 section 6.2)."""
    employee.current_salary_record_id = record.id
    employee.currency = record.currency
    employee.current_base_minor = record.base_minor
    employee.current_total_minor = record.total_minor
