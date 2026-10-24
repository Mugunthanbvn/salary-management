"""POST /employees/{id}/salary-changes appends to the salary history (docs/07-api-spec.md 6.7)."""

from datetime import date
from typing import Any

import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees.models import Employee
from salary_api.modules.salaries.models import SalaryRecord
from tests.conftest import signed_in_client
from tests.factories import make_employee, make_job_role, make_user

EMPLOYEES = "/api/v1/employees"
PROBLEMS = "https://acme.example/problems/"


def salary_change(**overrides: Any) -> dict[str, Any]:
    """A valid MERIT change effective on the frozen today, 2026-10-01."""
    body: dict[str, Any] = {
        "version": 1,
        "effective_date": "2026-10-01",
        "reason": "MERIT",
        "base_minor": 216_000_000,
        "components": [{"type": "ALLOWANCE", "name": "HRA", "amount_minor": 86_400_000}],
        "note": "Annual cycle 2026",
    }
    return body | overrides


def test_salary_change_appends_record_and_updates_current_salary(
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
        level="L3",
        base_minor=180_000_000,
        components=[("ALLOWANCE", "HRA", 72_000_000)],
        hire_date=date(2021, 3, 15),
    )

    response = signed_in_client(app, hr, settings).post(
        f"{EMPLOYEES}/{employee.id}/salary-changes", json=salary_change()
    )

    assert response.status_code == 201
    body = response.json()
    inr = "INR"
    assert body == {
        "record": {
            "id": body["record"]["id"],
            "effective_date": "2026-10-01",
            "reason": "MERIT",
            "job_role": {"id": role.id, "title": "Software Engineer"},
            "level": "L3",
            "base": {"amount_minor": 216_000_000, "currency": inr},
            "total": {"amount_minor": 302_400_000, "currency": inr},
            "components": [
                {
                    "type": "ALLOWANCE",
                    "name": "HRA",
                    "amount": {"amount_minor": 86_400_000, "currency": inr},
                }
            ],
            "base_change_pct": "20.00",
            "changed_by": {"id": hr.id, "full_name": "Harriet Rao"},
            "note": "Annual cycle 2026",
            "created_at": "2026-10-01T09:00:00Z",
        },
        "employee_version": 2,
    }
    stored = db_session.get(Employee, employee.id)
    assert stored is not None
    assert (
        stored.current_salary_record_id,
        stored.current_base_minor,
        stored.current_total_minor,
    ) == (
        body["record"]["id"],
        216_000_000,
        302_400_000,
    )
    records = db_session.scalars(
        select(SalaryRecord).where(SalaryRecord.employee_id == employee.id)
    ).all()
    assert [record.reason for record in records] == ["HIRE", "MERIT"]


def test_salary_change_writes_one_salary_change_event(
    app: FastAPI,
    client: TestClient,
    db_session: Session,
    settings: Settings,
    frozen_time: time_machine.Traveller,
) -> None:
    hr = make_user(db_session, role="HR_MANAGER")
    employee = make_employee(db_session, country="IN", base_minor=180_000_000)

    response = signed_in_client(app, hr, settings).post(
        f"{EMPLOYEES}/{employee.id}/salary-changes", json=salary_change()
    )

    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.actor_id, event.entity, event.entity_id) == (
        "salary.change",
        hr.id,
        "employee",
        str(employee.id),
    )
    assert event.diff == {
        "salary_record_id": response.json()["record"]["id"],
        "reason": "MERIT",
        "effective_date": "2026-10-01",
        "base_minor": [180_000_000, 216_000_000],
    }
