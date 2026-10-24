"""POST /employees creates the employee and its HIRE salary record (docs/07-api-spec.md 6.2)."""

from collections.abc import Callable

import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.modules.employees.models import Employee
from salary_api.modules.salaries.models import SalaryRecord
from tests.conftest import signed_in_client
from tests.factories import employee_request, make_country, make_job_role, make_user

EMPLOYEES = "/api/v1/employees"
PROBLEMS = "https://acme.example/problems/"


def test_create_employee_returns_201_and_location(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    role = make_job_role(db_session, "Software Engineer")
    make_country(db_session, "DE")

    response = as_role("HR_MANAGER").post(
        EMPLOYEES, json=employee_request(role.id, employee_code="ACME-010001")
    )

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"{EMPLOYEES}/{body['id']}"
    eur = "EUR"
    assert body == {
        "id": body["id"],
        "employee_code": "ACME-010001",
        "first_name": "Lena",
        "last_name": "Müller",
        "email": "lena.mueller@acme.example",
        "job_role": {"id": role.id, "title": "Software Engineer"},
        "department": {"id": role.department_id, "name": "Engineering"},
        "level": "L2",
        "employment_type": "FULL_TIME",
        "country_code": "DE",
        "status": "ACTIVE",
        "hire_date": "2026-09-01",
        "termination_date": None,
        "current_base": {"amount_minor": 5_400_000, "currency": eur},
        "current_total": {"amount_minor": 5_892_000, "currency": eur},
        "current_salary": {
            "id": body["current_salary"]["id"],
            "effective_date": "2026-09-01",
            "reason": "HIRE",
            "components": [
                {
                    "type": "ALLOWANCE",
                    "name": "Transport",
                    "amount": {"amount_minor": 60_000, "currency": eur},
                },
                {
                    "type": "BONUS_TARGET",
                    "name": "Target bonus",
                    "amount": {"amount_minor": 432_000, "currency": eur},
                },
            ],
        },
        "salary_masked": False,
        "version": 1,
    }


def test_create_employee_writes_the_hire_record_and_points_the_employee_at_it(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    hr = make_user(db_session, role="HR_MANAGER")
    role = make_job_role(db_session)
    make_country(db_session, "DE")

    response = signed_in_client(app, hr, settings).post(
        EMPLOYEES, json=employee_request(role.id, employee_code="ACME-000001")
    )

    employee = db_session.get(Employee, response.json()["id"])
    assert employee is not None
    record = db_session.scalars(
        select(SalaryRecord).where(SalaryRecord.employee_id == employee.id)
    ).one()
    assert employee.current_salary_record_id == record.id
    assert (record.reason, record.effective_date, record.currency) == (
        "HIRE",
        employee.hire_date,
        "EUR",
    )
    assert (record.base_minor, record.total_minor) == (5_400_000, 5_892_000)
    assert (record.job_role_id, record.level) == (role.id, "L2")
    assert (record.changed_by, record.note) == (hr.id, "Offer accepted 2026-08-12")
    assert (employee.currency, employee.current_base_minor, employee.current_total_minor) == (
        "EUR",
        5_400_000,
        5_892_000,
    )
    assert employee.search_text == "lena muller acme-000001 lena.mueller@acme.example"
