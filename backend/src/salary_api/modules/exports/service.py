"""Export the employee list as CSV or XLSX (docs/11-import-export.md section 6).

The rows are exactly those the list shows for the same filters and sort, with the same
refusals (salary filters and sorts need SALARY_READ). Without SALARY_READ the salary
columns are left out of the file altogether, here in the service.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from salary_api.core.downloads import MEDIA_TYPES, DownloadFile
from salary_api.core.models import utc_now
from salary_api.core.permissions import Principal
from salary_api.core.schemas import FileFormat
from salary_api.domain.enums import ComponentType
from salary_api.domain.money import FxRate, Money, to_usd
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import service as employees
from salary_api.modules.employees.models import Employee
from salary_api.modules.exports.schemas import EmployeeExportQuery
from salary_api.modules.exports.writers import CellValue, csv_bytes, xlsx_bytes
from salary_api.modules.reference import service as reference
from salary_api.modules.salaries import repository as salaries

# In the import template's order where the two overlap (docs/11 section 6.2).
PROFILE_COLUMNS: Final = (
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "job_role",
    "level",
    "employment_type",
    "country",
    "hire_date",
    "department",
    "status",
)
# Only for callers with SALARY_READ. Amounts are annual, in major units.
SALARY_COLUMNS: Final = (
    "currency",
    "base_salary",
    "bonus_target",
    "allowances_total",
    "total_comp",
    "base_salary_usd",
    "total_comp_usd",
    "fx_as_of",
)
SHEET_TITLE: Final = "Employees"


def export_employees(
    session: Session, principal: Principal, query: EmployeeExportQuery
) -> DownloadFile:
    """The filtered, sorted list as a file, and an export.download audit event."""
    matched = employees.matching_employees(session, principal, query)
    salary_included = employees.can_see_salaries(principal)
    header = PROFILE_COLUMNS + (SALARY_COLUMNS if salary_included else ())
    rows = [_profile(employee) for employee in matched]
    if salary_included:
        rows = _with_salaries(session, matched, rows)
    content = (
        csv_bytes(header, rows)
        if query.format == FileFormat.CSV
        else xlsx_bytes(SHEET_TITLE, header, rows)
    )
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.EXPORT_DOWNLOAD,
        entity="employee",
        entity_id=None,
        diff={
            "format": query.format,
            "filters": _filters(query),
            "row_count": len(rows),
            "salary_included": salary_included,
        },
    )
    session.commit()
    return DownloadFile(
        content=content,
        media_type=MEDIA_TYPES[query.format],
        filename=f"acme-employees-{utc_now().date().isoformat()}.{query.format}",
    )


def _profile(employee: Employee) -> list[CellValue]:
    role = employee.job_role
    return [
        employee.employee_code,
        employee.first_name,
        employee.last_name,
        employee.email,
        role.title,
        employee.level,
        employee.employment_type,
        employee.country_code,
        employee.hire_date,
        role.department.name,
        employee.status,
    ]


def _with_salaries(
    session: Session, matched: Sequence[Employee], rows: list[list[CellValue]]
) -> list[list[CellValue]]:
    """Each row with the current salary: base, components, total, and USD where a rate is set."""
    record_ids = [e.current_salary_record_id for e in matched if e.current_salary_record_id]
    totals = salaries.component_totals(session, record_ids)
    rates = reference.usd_rates(session)
    return [
        row + _salary(employee, totals.get(employee.current_salary_record_id or 0, {}), rates)
        for employee, row in zip(matched, rows, strict=True)
    ]


def _salary(
    employee: Employee, components: Mapping[ComponentType, int], rates: Mapping[str, FxRate]
) -> list[CellValue]:
    currency = employee.currency
    base = Money(employee.current_base_minor, currency)
    total = Money(employee.current_total_minor, currency)
    rate = rates.get(currency)
    base_usd = to_usd(base, rates) if rate else None
    total_usd = to_usd(total, rates) if rate else None
    return [
        currency,
        base.to_major(),
        Money(components.get(ComponentType.BONUS_TARGET, 0), currency).to_major(),
        Money(components.get(ComponentType.ALLOWANCE, 0), currency).to_major(),
        total.to_major(),
        # Blank, never a guessed rate, for a currency without a USD rate.
        base_usd.amount.to_major() if base_usd else None,
        total_usd.amount.to_major() if total_usd else None,
        rate.as_of if rate else None,
    ]


def _filters(query: EmployeeExportQuery) -> dict[str, Any]:
    """The filters and sort in effect, for the audit event."""
    given = query.model_dump(mode="json", exclude={"format"}, exclude_none=True)
    return {name: value for name, value in given.items() if value != []}
