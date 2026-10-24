"""The employees, salary_records and salary_components tables (docs/06-data-model.md 4.5-4.7)."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import inspect, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from salary_api.domain.enums import (
    ComponentType,
    EmployeeStatus,
    EmploymentType,
    Level,
    SalaryReason,
)
from salary_api.modules.employees.models import Employee
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from tests.factories import make_country, make_job_role


def _employee(session: Session, **overrides: Any) -> Employee:
    values: dict[str, Any] = {
        "employee_code": "ACME-000001",
        "first_name": "Lena",
        "last_name": "Müller",
        "email": "lena.mueller@acme.example",
        "search_text": "lena muller acme-000001 lena.mueller@acme.example",
        "job_role_id": make_job_role(session).id,
        "level": Level.L2,
        "employment_type": EmploymentType.FULL_TIME,
        "country_code": make_country(session, "DE").code,
        "hire_date": date(2024, 1, 15),
        "currency": "EUR",
        "current_base_minor": 5_400_000,
        "current_total_minor": 5_460_000,
    }
    employee = Employee(**(values | overrides))
    session.add(employee)
    session.flush()
    return employee


def _record(session: Session, employee: Employee, **overrides: Any) -> SalaryRecord:
    values: dict[str, Any] = {
        "employee_id": employee.id,
        "effective_date": employee.hire_date,
        "currency": employee.currency,
        "base_minor": employee.current_base_minor,
        "total_minor": employee.current_total_minor,
        "job_role_id": employee.job_role_id,
        "level": employee.level,
        "reason": SalaryReason.HIRE,
    }
    record = SalaryRecord(**(values | overrides))
    session.add(record)
    session.flush()
    return record


def test_an_employee_starts_active_at_version_1_and_points_at_its_hire_record(
    db_session: Session,
) -> None:
    employee = _employee(db_session)
    record = _record(
        db_session,
        employee,
        components=[
            SalaryComponent(type=ComponentType.ALLOWANCE, name="Transport", amount_minor=60_000)
        ],
    )
    employee.current_salary_record_id = record.id
    db_session.flush()
    db_session.expunge_all()

    stored = db_session.get(Employee, employee.id)

    assert stored is not None
    assert (stored.status, stored.termination_date, stored.version) == (
        EmployeeStatus.ACTIVE,
        None,
        1,
    )
    assert stored.current_salary_record is not None
    assert stored.current_salary_record.reason == SalaryReason.HIRE
    assert [(c.type, c.name, c.amount_minor) for c in stored.current_salary_record.components] == [
        (ComponentType.ALLOWANCE, "Transport", 60_000)
    ]


def test_an_employee_email_is_stored_trimmed_and_lowercased(db_session: Session) -> None:
    employee = _employee(db_session, email="  Lena.Mueller@ACME.example ")

    assert employee.email == "lena.mueller@acme.example"


@pytest.mark.parametrize("column", ["employee_code", "email"])
def test_two_employees_cannot_share_a_code_or_an_email(db_session: Session, column: str) -> None:
    first = _employee(db_session)
    other = {"employee_code": "ACME-000002", "email": "other@acme.example"}

    with pytest.raises(IntegrityError, match="UNIQUE"):
        _employee(db_session, **(other | {column: getattr(first, column)}))


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"status": EmployeeStatus.TERMINATED}, id="terminated without a date"),
        pytest.param({"termination_date": date(2025, 1, 1)}, id="active with a date"),
        pytest.param(
            {"status": EmployeeStatus.TERMINATED, "termination_date": date(2023, 12, 31)},
            id="terminated before hire",
        ),
        pytest.param({"current_base_minor": 0}, id="base not positive"),
        pytest.param({"current_total_minor": 5_000_000}, id="total below base"),
    ],
)
def test_the_database_rejects_an_employee_that_cannot_be_right(
    db_session: Session, overrides: dict[str, Any]
) -> None:
    with pytest.raises(IntegrityError, match="CHECK"):
        _employee(db_session, **overrides)


def test_a_terminated_employee_has_a_termination_date_on_or_after_hire(
    db_session: Session,
) -> None:
    employee = _employee(
        db_session, status=EmployeeStatus.TERMINATED, termination_date=date(2024, 1, 15)
    )

    assert employee.status == EmployeeStatus.TERMINATED


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"base_minor": 0, "total_minor": 0}, id="base not positive"),
        pytest.param({"total_minor": 5_000_000}, id="total below base"),
    ],
)
def test_the_database_rejects_a_salary_record_that_cannot_be_right(
    db_session: Session, overrides: dict[str, Any]
) -> None:
    employee = _employee(db_session)

    with pytest.raises(IntegrityError, match="CHECK"):
        _record(db_session, employee, **overrides)


def test_the_database_rejects_a_negative_component(db_session: Session) -> None:
    employee = _employee(db_session)
    negative = SalaryComponent(
        type=ComponentType.BONUS_TARGET, name="Target bonus", amount_minor=-1
    )

    with pytest.raises(IntegrityError, match="CHECK"):
        _record(db_session, employee, components=[negative])


def test_a_record_cannot_have_two_components_of_the_same_type_and_name(
    db_session: Session,
) -> None:
    employee = _employee(db_session)
    twice = [
        SalaryComponent(type=ComponentType.ALLOWANCE, name="Transport", amount_minor=amount)
        for amount in (60_000, 70_000)
    ]

    with pytest.raises(IntegrityError, match="UNIQUE"):
        _record(db_session, employee, components=twice)


def test_a_stale_version_cannot_overwrite_a_newer_row(db_session: Session) -> None:
    employee = _employee(db_session)
    db_session.execute(
        update(Employee).where(Employee.id == employee.id).values(version=2),
        execution_options={"synchronize_session": False},
    )

    employee.first_name = "Lene"
    employee.version = 2  # the session still believes the row is at version 1

    with pytest.raises(StaleDataError):
        db_session.flush()


def test_employee_indexes_serve_the_list_filters_and_sorts(db_session: Session) -> None:
    indexes = {
        index["name"]: index["column_names"]
        for index in inspect(db_session.connection()).get_indexes("employees")
    }

    assert indexes == {
        "ix_employees_country_status": ["country_code", "status"],
        "ix_employees_job_role_level": ["job_role_id", "level"],
        "ix_employees_status_employment_type": ["status", "employment_type"],
        "ix_employees_currency_base": ["currency", "current_base_minor"],
        "ix_employees_last_first": ["last_name", "first_name"],
        # No index on search_text: infix LIKE '%term%' cannot use one (a 10k-row scan).
    }


def test_salary_indexes_serve_the_timeline_and_the_components(db_session: Session) -> None:
    connection = inspect(db_session.connection())

    record_indexes = {
        i["name"]: i["column_names"] for i in connection.get_indexes("salary_records")
    }
    component_indexes = {
        i["name"]: i["column_names"] for i in connection.get_indexes("salary_components")
    }

    assert record_indexes == {
        "ix_salary_records_employee_effective": ["employee_id", "effective_date", "id"],
        "ix_salary_records_effective_reason": ["effective_date", "reason"],
    }
    assert component_indexes == {"ix_salary_components_record": ["salary_record_id"]}
