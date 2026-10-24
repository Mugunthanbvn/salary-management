"""PATCH /employees/{id}: profile fields only, with optimistic locking (docs/07-api-spec.md 6.4)."""

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import VersionConflict
from salary_api.core.permissions import Principal, Role
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees import service
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.schemas import EmployeeUpdate
from tests.conftest import signed_in_client
from tests.factories import make_employee, make_user

EMPLOYEES = "/api/v1/employees"
PROBLEMS = "https://acme.example/problems/"


def test_patch_changes_profile_fields_and_returns_the_next_version(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(
        db_session, first_name="Priya", last_name="Sharma", email="priya@acme.example"
    )

    response = as_role("HR_MANAGER").patch(
        f"{EMPLOYEES}/{employee.id}",
        json={
            "version": 1,
            "first_name": "Priyanka",
            "last_name": "Šarma",
            "email": " Priyanka.S@ACME.example ",
            "employment_type": "PART_TIME",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["first_name"], body["last_name"], body["email"]) == (
        "Priyanka",
        "Šarma",
        "priyanka.s@acme.example",
    )
    assert (body["employment_type"], body["version"]) == ("PART_TIME", 2)
    stored = db_session.get(Employee, employee.id)
    assert stored is not None
    assert (
        stored.search_text
        == f"priyanka sarma {employee.employee_code.lower()} priyanka.s@acme.example"
    )


def test_patch_of_an_unknown_employee_is_404(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("HR_MANAGER").patch(f"{EMPLOYEES}/999", json={"version": 1})

    assert response.status_code == 404


def test_patch_with_a_stale_version_is_409_with_the_current_version(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session, first_name="Priya")
    hr = as_role("HR_MANAGER")
    url = f"{EMPLOYEES}/{employee.id}"
    hr.patch(url, json={"version": 1, "first_name": "Asha"})

    response = hr.patch(url, json={"version": 1, "first_name": "Bina"})

    assert response.status_code == 409
    assert (response.json()["type"], response.json()["current_version"]) == (
        f"{PROBLEMS}version-conflict",
        2,
    )
    assert hr.get(url).json()["first_name"] == "Asha"


def test_a_change_committed_between_read_and_write_is_a_version_conflict(
    db_session: Session,
) -> None:
    employee = make_employee(db_session)
    db_session.commit()
    # Another request commits version 2 after this session read version 1.
    db_session.execute(
        update(Employee).where(Employee.id == employee.id).values(version=2),
        execution_options={"synchronize_session": False},
    )
    db_session.commit()
    hr = Principal(user_id=1, email="hr@acme.example", full_name="HR", role=Role.HR_MANAGER)

    with pytest.raises(VersionConflict) as conflict:
        service.update_employee(
            db_session, hr, employee.id, EmployeeUpdate(version=1, first_name="Late")
        )

    assert conflict.value.extra["current_version"] == 2


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"version": 1, "job_role_id": 2}, id="role"),
        pytest.param({"version": 1, "level": "L4"}, id="level"),
        pytest.param({"version": 1, "country_code": "FR"}, id="country"),
        pytest.param({"version": 1, "current_base_minor": 1}, id="salary"),
        pytest.param({"version": 1, "status": "TERMINATED"}, id="status"),
        pytest.param({"first_name": "No version"}, id="no version"),
        pytest.param({"version": 1, "first_name": None}, id="null name"),
        pytest.param({"version": 1, "employment_type": None}, id="null employment type"),
        pytest.param({"version": 1, "email": "not-an-email"}, id="bad email"),
    ],
)
def test_patch_refuses_anything_but_profile_fields(
    as_role: Callable[[str], TestClient], db_session: Session, body: dict[str, object]
) -> None:
    employee = make_employee(db_session)

    response = as_role("HR_MANAGER").patch(f"{EMPLOYEES}/{employee.id}", json=body)

    assert response.status_code == 422
    assert response.json()["type"] == f"{PROBLEMS}validation"
    assert employee.version == 1


def test_patch_refuses_an_email_another_employee_uses(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_employee(db_session, email="taken@acme.example")
    employee = make_employee(db_session)

    response = as_role("HR_MANAGER").patch(
        f"{EMPLOYEES}/{employee.id}", json={"version": 1, "email": "TAKEN@acme.example"}
    )

    assert response.status_code == 409
    assert response.json()["type"] == f"{PROBLEMS}duplicate"


def test_patch_may_resend_the_employee_s_own_email(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session, email="me@acme.example")

    response = as_role("HR_MANAGER").patch(
        f"{EMPLOYEES}/{employee.id}", json={"version": 1, "email": "ME@acme.example"}
    )

    assert response.status_code == 200


def test_patch_writes_one_employee_update_event_with_old_and_new_values(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> None:
    hr = make_user(db_session, role="HR_MANAGER")
    employee = make_employee(db_session, first_name="Priya", last_name="Sharma")

    signed_in_client(app, hr, settings).patch(
        f"{EMPLOYEES}/{employee.id}",
        json={
            "version": 1,
            "first_name": "Priyanka",
            "last_name": "Sharma",  # unchanged: not in the diff
            "employment_type": "PART_TIME",
        },
    )

    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.actor_id, event.entity, event.entity_id) == (
        "employee.update",
        hr.id,
        "employee",
        str(employee.id),
    )
    assert event.diff == {
        "first_name": ["Priya", "Priyanka"],
        "employment_type": ["FULL_TIME", "PART_TIME"],
    }


def test_a_patch_that_changes_nothing_writes_nothing_and_keeps_the_version(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session, first_name="Priya")

    response = as_role("HR_MANAGER").patch(
        f"{EMPLOYEES}/{employee.id}", json={"version": 1, "first_name": "Priya"}
    )

    assert (response.status_code, response.json()["version"]) == (200, 1)
    assert db_session.scalars(select(AuditEvent)).all() == []
