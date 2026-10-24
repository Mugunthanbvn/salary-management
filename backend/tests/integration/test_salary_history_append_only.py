"""Salary history is append-only, like audit events (ADR 0006, docs/06-data-model.md 4.6)."""

from datetime import date
from typing import Any, cast

import pytest
from sqlalchemy import Table, delete, update
from sqlalchemy.orm import Session

from salary_api.core.append_only import AppendOnlyError
from salary_api.domain.enums import ComponentType, EmploymentType, Level, SalaryReason
from salary_api.modules.employees.models import Employee
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from tests.factories import make_country, make_job_role


def _record_with_a_component(session: Session) -> SalaryRecord:
    role = make_job_role(session)
    employee = Employee(
        employee_code="ACME-000001",
        first_name="Lena",
        last_name="Müller",
        email="lena@acme.example",
        search_text="lena muller acme-000001 lena@acme.example",
        job_role_id=role.id,
        level=Level.L2,
        employment_type=EmploymentType.FULL_TIME,
        country_code=make_country(session, "DE").code,
        hire_date=date(2024, 1, 15),
        currency="EUR",
        current_base_minor=5_400_000,
        current_total_minor=5_460_000,
    )
    session.add(employee)
    session.flush()
    record = SalaryRecord(
        employee_id=employee.id,
        effective_date=employee.hire_date,
        currency="EUR",
        base_minor=5_400_000,
        total_minor=5_460_000,
        job_role_id=role.id,
        level=Level.L2,
        reason=SalaryReason.HIRE,
        components=[
            SalaryComponent(type=ComponentType.ALLOWANCE, name="Transport", amount_minor=60_000)
        ],
    )
    session.add(record)
    session.flush()
    return record


def test_a_salary_record_cannot_be_changed_after_it_is_written(db_session: Session) -> None:
    record = _record_with_a_component(db_session)

    record.base_minor = 9_999_999

    with pytest.raises(AppendOnlyError):
        db_session.flush()


def test_a_salary_record_cannot_be_deleted(db_session: Session) -> None:
    record = _record_with_a_component(db_session)

    db_session.delete(record)

    with pytest.raises(AppendOnlyError):
        db_session.flush()


@pytest.mark.parametrize("change", ["update", "delete"])
def test_a_salary_component_cannot_be_changed_or_deleted(db_session: Session, change: str) -> None:
    component = _record_with_a_component(db_session).components[0]

    if change == "update":
        component.amount_minor = 0
    else:
        db_session.delete(component)

    with pytest.raises(AppendOnlyError):
        db_session.flush()


RECORDS = cast(Table, SalaryRecord.__table__)
COMPONENTS = cast(Table, SalaryComponent.__table__)


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param(update(SalaryRecord).values(base_minor=1), id="orm record update"),
        pytest.param(delete(SalaryRecord), id="orm record delete"),
        pytest.param(update(RECORDS).values(base_minor=1), id="table record update"),
        pytest.param(delete(COMPONENTS), id="table component delete"),
        pytest.param(update(SalaryComponent).values(amount_minor=0), id="orm component update"),
    ],
)
def test_bulk_statements_cannot_change_or_delete_salary_history(
    db_session: Session, statement: Any
) -> None:
    _record_with_a_component(db_session)

    with pytest.raises(AppendOnlyError):
        db_session.execute(statement)
