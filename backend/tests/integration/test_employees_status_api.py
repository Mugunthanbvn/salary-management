"""Terminate and reactivate (docs/07-api-spec.md 6.5, docs/06-data-model.md 6.3, ADR 0013)."""

from collections.abc import Callable
from datetime import date

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.modules.audit.models import AuditEvent
from tests.conftest import signed_in_client
from tests.factories import make_employee, make_user

EMPLOYEES = "/api/v1/employees"
PROBLEMS = "https://acme.example/problems/"


def test_terminate_sets_the_status_and_date_and_writes_one_event(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    hr = make_user(db_session, role="HR_MANAGER")
    employee = make_employee(db_session)

    response = signed_in_client(app, hr, settings).post(
        f"{EMPLOYEES}/{employee.id}/terminate",
        json={"version": 1, "termination_date": "2026-10-31", "note": "Resigned"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["termination_date"], body["version"]) == (
        "TERMINATED",
        "2026-10-31",
        2,
    )
    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.actor_id, event.entity_id) == (
        "employee.terminate",
        hr.id,
        str(employee.id),
    )
    assert event.diff == {
        "status": ["ACTIVE", "TERMINATED"],
        "termination_date": [None, "2026-10-31"],
        "note": "Resigned",
    }


def test_terminate_defaults_the_date_to_today(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
) -> None:
    employee = make_employee(db_session)

    response = as_role("HR_MANAGER").post(
        f"{EMPLOYEES}/{employee.id}/terminate", json={"version": 1}
    )

    assert response.json()["termination_date"] == "2026-10-01"


def test_reactivate_clears_the_termination_and_writes_one_event(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    hr = make_user(db_session, role="HR_MANAGER")
    employee = make_employee(db_session, status="TERMINATED", termination_date=date(2025, 6, 30))

    response = signed_in_client(app, hr, settings).post(
        f"{EMPLOYEES}/{employee.id}/reactivate", json={"version": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["termination_date"], body["version"]) == ("ACTIVE", None, 2)
    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.actor_id, event.entity_id) == (
        "employee.reactivate",
        hr.id,
        str(employee.id),
    )
    assert event.diff == {
        "status": ["TERMINATED", "ACTIVE"],
        "termination_date": ["2025-06-30", None],
    }


@pytest.mark.parametrize(
    ("status", "action"), [("TERMINATED", "terminate"), ("ACTIVE", "reactivate")]
)
def test_moving_an_employee_to_the_status_they_have_is_409_invalid_state(
    as_role: Callable[[str], TestClient], db_session: Session, status: str, action: str
) -> None:
    employee = make_employee(db_session, status=status)

    response = as_role("HR_MANAGER").post(
        f"{EMPLOYEES}/{employee.id}/{action}", json={"version": 1}
    )

    assert response.status_code == 409
    assert response.json()["type"] == f"{PROBLEMS}invalid-state"
    assert db_session.scalars(select(AuditEvent)).all() == []


def test_a_termination_date_before_the_hire_date_is_refused(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session, hire_date=date(2024, 1, 15))

    response = as_role("HR_MANAGER").post(
        f"{EMPLOYEES}/{employee.id}/terminate",
        json={"version": 1, "termination_date": "2024-01-14"},
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", "termination_date"]


@pytest.mark.parametrize(
    ("status", "action"), [("ACTIVE", "terminate"), ("TERMINATED", "reactivate")]
)
def test_a_status_change_with_a_stale_version_is_a_version_conflict(
    as_role: Callable[[str], TestClient], db_session: Session, status: str, action: str
) -> None:
    employee = make_employee(db_session, status=status)

    response = as_role("HR_MANAGER").post(
        f"{EMPLOYEES}/{employee.id}/{action}", json={"version": 7}
    )

    assert (response.status_code, response.json()["current_version"]) == (409, 1)
