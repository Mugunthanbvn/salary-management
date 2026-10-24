"""Terminate and reactivate (docs/07-api-spec.md 6.5, docs/06-data-model.md 6.3, ADR 0013)."""

from collections.abc import Callable

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
