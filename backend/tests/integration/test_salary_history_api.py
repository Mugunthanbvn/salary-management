"""GET /employees/{id}/salary-history (docs/07-api-spec.md 6.6). SALARY_READ only."""

from collections.abc import Callable
from datetime import date

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import Forbidden
from salary_api.core.permissions import Principal, Role
from salary_api.modules.salaries import service
from tests.conftest import signed_in_client
from tests.factories import make_country, make_employee, make_job_role, make_user

EMPLOYEES = "/api/v1/employees"


def test_history_lists_records_by_effective_date_with_the_change_in_base(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    hr = make_user(db_session, role="HR_MANAGER", full_name="Harriet Rao")
    role = make_job_role(db_session, "Software Engineer")
    employee = make_employee(
        db_session,
        country="IN",
        job_role=role,
        level="L2",
        base_minor=180_000_000,
        components=[("ALLOWANCE", "HRA", 72_000_000)],
        hire_date=date(2021, 3, 15),
    )  # a seeded HIRE record: changed_by is null
    hire_record_id = employee.current_salary_record_id
    http = signed_in_client(app, hr, settings)
    changes = f"{EMPLOYEES}/{employee.id}/salary-changes"
    http.post(
        changes,
        json={
            "version": 1,
            "effective_date": "2023-04-01",
            "reason": "PROMOTION",
            "level": "L3",
            "base_minor": 216_000_000,
        },
    )
    http.post(
        changes,
        json={
            "version": 2,
            "effective_date": "2026-10-01",
            "reason": "MERIT",
            "base_minor": 226_800_000,
            "note": "Annual cycle 2026",
        },
    )

    response = http.get(f"{EMPLOYEES}/{employee.id}/salary-history")

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == employee.id
    hire, promotion, merit = body["records"]
    inr = "INR"
    assert hire == {
        "id": hire_record_id,
        "effective_date": "2021-03-15",
        "reason": "HIRE",
        "job_role": {"id": role.id, "title": "Software Engineer"},
        "level": "L2",
        "base": {"amount_minor": 180_000_000, "currency": inr},
        "total": {"amount_minor": 252_000_000, "currency": inr},
        "components": [
            {
                "type": "ALLOWANCE",
                "name": "HRA",
                "amount": {"amount_minor": 72_000_000, "currency": inr},
            }
        ],
        "base_change_pct": None,
        "changed_by": None,
        "note": None,
        "created_at": "2026-10-01T09:00:00Z",
    }
    assert (promotion["reason"], promotion["level"], promotion["base_change_pct"]) == (
        "PROMOTION",
        "L3",
        "20.00",
    )
    assert promotion["changed_by"] == {"id": hr.id, "full_name": "Harriet Rao"}
    assert promotion["components"] == []
    assert (merit["reason"], merit["base_change_pct"], merit["note"]) == (
        "MERIT",
        "5.00",
        "Annual cycle 2026",
    )


def test_records_on_the_same_day_keep_the_order_they_were_written(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    employee = make_employee(db_session, hire_date=date(2026, 10, 1), base_minor=6_000_000)
    hr = as_role("HR_MANAGER")
    hr.post(
        f"{EMPLOYEES}/{employee.id}/salary-changes",
        json={
            "version": 1,
            "effective_date": "2026-10-01",
            "reason": "CORRECTION",
            "base_minor": 6_300_000,
        },
    )

    records = hr.get(f"{EMPLOYEES}/{employee.id}/salary-history").json()["records"]

    assert [(r["reason"], r["base_change_pct"]) for r in records] == [
        ("HIRE", None),
        ("CORRECTION", "5.00"),
    ]


def test_the_change_in_base_is_null_after_a_relocation(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    employee = make_employee(db_session, country="DE")
    make_country(db_session, "US")
    hr = as_role("HR_MANAGER")
    hr.post(
        f"{EMPLOYEES}/{employee.id}/salary-changes",
        json={
            "version": 1,
            "effective_date": "2026-10-01",
            "reason": "MARKET_ADJUSTMENT",
            "country_code": "US",
            "base_minor": 9_000_000,
        },
    )

    records = hr.get(f"{EMPLOYEES}/{employee.id}/salary-history").json()["records"]

    assert [r["base_change_pct"] for r in records] == [None, None]


def test_viewer_cannot_see_salary_history(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session)

    response = as_role("VIEWER").get(f"{EMPLOYEES}/{employee.id}/salary-history")

    assert response.status_code == 403


def test_the_service_refuses_salary_history_without_salary_read(db_session: Session) -> None:
    employee = make_employee(db_session)
    viewer = Principal(user_id=1, email="v@acme.example", full_name="V", role=Role.VIEWER)

    with pytest.raises(Forbidden):
        service.salary_history(db_session, viewer, employee.id)


def test_history_of_an_unknown_employee_is_404(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("HR_MANAGER").get(f"{EMPLOYEES}/999/salary-history")

    assert response.status_code == 404
