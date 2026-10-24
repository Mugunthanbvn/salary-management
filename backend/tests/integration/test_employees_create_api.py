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
from salary_api.domain.constants import MAX_AMOUNT_MINOR
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees.models import Employee
from salary_api.modules.salaries.models import SalaryRecord
from tests.conftest import signed_in_client
from tests.factories import (
    employee_request,
    make_country,
    make_employee,
    make_job_role,
    make_user,
)

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


def _component(**overrides: Any) -> dict[str, Any]:
    return {"type": "ALLOWANCE", "name": "Transport", "amount_minor": 60_000} | overrides


MALFORMED = [
    ("base is a fraction", {"salary": _salary(base_minor=5_400_000.5)}, ["salary", "base_minor"]),
    ("base is a float", {"salary": _salary(base_minor=5_400_000.0)}, ["salary", "base_minor"]),
    ("base is text", {"salary": _salary(base_minor="5400000")}, ["salary", "base_minor"]),
    ("base is zero", {"salary": _salary(base_minor=0)}, ["salary", "base_minor"]),
    (
        "base is too large",
        {"salary": _salary(base_minor=MAX_AMOUNT_MINOR + 1)},
        ["salary", "base_minor"],
    ),
    (
        "component is negative",
        {"salary": _salary(components=[_component(amount_minor=-1)])},
        ["salary", "components", 0, "amount_minor"],
    ),
    (
        "component is too large",
        {"salary": _salary(components=[_component(amount_minor=MAX_AMOUNT_MINOR + 1)])},
        ["salary", "components", 0, "amount_minor"],
    ),
    (
        "component is a float",
        {"salary": _salary(components=[_component(amount_minor=1.0)])},
        ["salary", "components", 0, "amount_minor"],
    ),
    (
        "component name is blank",
        {"salary": _salary(components=[_component(name="  ")])},
        ["salary", "components", 0, "name"],
    ),
    (
        "component listed twice",
        {"salary": _salary(components=[_component(), _component(amount_minor=1)])},
        ["salary", "components"],
    ),
    (
        "more than 20 components",
        {"salary": _salary(components=[_component(name=f"A{n}") for n in range(21)])},
        ["salary", "components"],
    ),
    ("note is too long", {"salary": _salary(note="x" * 501)}, ["salary", "note"]),
    ("code is not ACME-######", {"employee_code": "EMP-1"}, ["employee_code"]),
    ("code has non-ASCII digits", {"employee_code": "ACME-" + "\u0661" * 6}, ["employee_code"]),
    ("email has no @", {"email": "lena.acme.example"}, ["email"]),
    ("first name is blank", {"first_name": "   "}, ["first_name"]),
    ("last name is too long", {"last_name": "x" * 101}, ["last_name"]),
    ("country code is lower case", {"country_code": "de"}, ["country_code"]),
    ("level is not in the glossary", {"level": "L9"}, ["level"]),
    ("an unknown field", {"department_id": 1}, ["department_id"]),
]


@pytest.mark.parametrize(
    ("overrides", "loc"),
    [pytest.param(overrides, loc, id=case) for case, overrides, loc in MALFORMED],
)
def test_create_refuses_a_malformed_request(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
    overrides: dict[str, Any],
    loc: list[str | int],
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "DE")

    response = as_role("HR_MANAGER").post(EMPLOYEES, json=employee_request(role.id) | overrides)

    assert response.status_code == 422
    assert response.json()["type"] == f"{PROBLEMS}validation"
    assert ["body", *loc] in [error["loc"] for error in response.json()["errors"]]


def test_a_code_outside_the_six_digit_format_is_not_the_highest(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_employee(db_session, employee_code="ACME-000041")
    make_employee(db_session, employee_code="ACME-1000000")  # e.g. written before validation
    role = make_job_role(db_session)

    response = as_role("HR_MANAGER").post(EMPLOYEES, json=employee_request(role.id))

    assert response.json()["employee_code"] == "ACME-000042"


def test_no_code_is_generated_past_acme_999999(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    make_employee(db_session, employee_code="ACME-999999")
    role = make_job_role(db_session)
    hr = as_role("HR_MANAGER")

    generated = hr.post(EMPLOYEES, json=employee_request(role.id))
    given = hr.post(EMPLOYEES, json=employee_request(role.id, employee_code="ACME-000001"))

    assert generated.status_code == 409
    assert generated.json()["type"] == f"{PROBLEMS}invalid-state"
    assert "ACME-999999" in generated.json()["detail"]
    assert given.status_code == 201


def test_create_reports_an_inactive_country_and_a_wrong_currency_together(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    role = make_job_role(db_session)
    make_country(db_session, "FR", is_active=False)

    response = as_role("HR_MANAGER").post(
        EMPLOYEES, json=employee_request(role.id, country_code="FR", salary=_salary(currency="USD"))
    )

    assert [(e["loc"], e["code"]) for e in response.json()["errors"]] == [
        (["body", "country_code"], "inactive"),
        (["body", "salary", "currency"], "currency_mismatch"),
    ]
