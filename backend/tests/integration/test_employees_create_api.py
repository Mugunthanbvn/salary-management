"""POST /employees creates the employee and its HIRE salary record (docs/07-api-spec.md 6.2)."""

from collections.abc import Callable
from typing import Any

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.modules.audit.models import AuditEvent
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


def test_create_employee_writes_one_audit_event_with_the_created_fields(
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

    body = response.json()
    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.actor_id, event.entity, event.entity_id) == (
        "employee.create",
        hr.id,
        "employee",
        str(body["id"]),
    )
    assert event.diff == {
        "employee_code": "ACME-000001",
        "first_name": "Lena",
        "last_name": "Müller",
        "email": "lena.mueller@acme.example",
        "job_role_id": role.id,
        "level": "L2",
        "employment_type": "FULL_TIME",
        "country_code": "DE",
        "hire_date": "2026-09-01",
        "salary_record_id": body["current_salary"]["id"],
    }


def test_an_omitted_employee_code_is_the_next_after_the_highest(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "DE")
    hr = as_role("HR_MANAGER")
    hr.post(
        EMPLOYEES,
        json=employee_request(role.id, employee_code="ACME-000041", email="a@acme.example"),
    )

    response = hr.post(EMPLOYEES, json=employee_request(role.id, email="b@acme.example"))

    assert response.status_code == 201
    assert response.json()["employee_code"] == "ACME-000042"
    employee = db_session.get(Employee, response.json()["id"])
    assert employee is not None
    assert "acme-000042" in employee.search_text


def test_the_first_generated_employee_code_is_acme_000001(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "DE")

    response = as_role("HR_MANAGER").post(EMPLOYEES, json=employee_request(role.id))

    assert response.json()["employee_code"] == "ACME-000001"


@pytest.mark.parametrize(
    ("field", "taken"),
    [("employee_code", "ACME-000007"), ("email", "  LENA.Mueller@Acme.Example ")],
)
def test_create_refuses_a_code_or_email_already_in_use(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
    field: str,
    taken: str,
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "DE")
    hr = as_role("HR_MANAGER")
    hr.post(EMPLOYEES, json=employee_request(role.id, employee_code="ACME-000007"))
    other = {"employee_code": "ACME-000008", "email": "other@acme.example"}

    response = hr.post(EMPLOYEES, json=employee_request(role.id, **(other | {field: taken})))

    assert response.status_code == 409
    assert response.json()["type"] == f"{PROBLEMS}duplicate"
    assert field in response.json()["detail"]
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 1
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1


def test_openapi_documents_the_problems_create_can_send(app: FastAPI) -> None:
    responses = app.openapi()["paths"][EMPLOYEES]["post"]["responses"]

    assert {"401", "403", "409", "422"} <= set(responses)
    assert responses["409"]["content"] == {
        "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}
    }


def _salary(**overrides: Any) -> dict[str, Any]:
    return {"base_minor": 5_400_000, "components": []} | overrides


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        pytest.param({"job_role_id": 999}, (["body", "job_role_id"], "not_found"), id="role"),
        pytest.param({"country_code": "XX"}, (["body", "country_code"], "not_found"), id="country"),
        pytest.param(
            {"country_code": "FR"}, (["body", "country_code"], "inactive"), id="inactive country"
        ),
        pytest.param(
            {"hire_date": "2026-10-02"}, (["body", "hire_date"], "future_date"), id="future hire"
        ),
        pytest.param(
            {"salary": _salary(currency="USD")},
            (["body", "salary", "currency"], "currency_mismatch"),
            id="not the country currency",
        ),
    ],
)
def test_create_refuses_values_that_break_a_business_rule(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
    overrides: dict[str, Any],
    error: tuple[list[str], str],
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "DE")
    make_country(db_session, "FR", is_active=False)

    response = as_role("HR_MANAGER").post(EMPLOYEES, json=employee_request(role.id) | overrides)

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == f"{PROBLEMS}validation"
    assert [(e["loc"], e["code"]) for e in body["errors"]] == [error]
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 0


def test_create_reports_every_broken_rule_at_once(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_country(db_session, "DE")

    response = as_role("HR_MANAGER").post(
        EMPLOYEES, json=employee_request(999, hire_date="2027-01-01")
    )

    assert [error["code"] for error in response.json()["errors"]] == ["not_found", "future_date"]


def test_create_accepts_the_country_currency_when_it_is_given(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "JP")

    response = as_role("HR_MANAGER").post(
        EMPLOYEES,
        json=employee_request(
            role.id, country_code="JP", salary=_salary(currency="JPY", base_minor=6_000_000)
        ),
    )

    assert response.status_code == 201
    assert response.json()["current_base"] == {"amount_minor": 6_000_000, "currency": "JPY"}
