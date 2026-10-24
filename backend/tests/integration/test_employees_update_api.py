"""PATCH /employees/{id}: profile fields only, with optimistic locking (docs/07-api-spec.md 6.4)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from salary_api.core.errors import VersionConflict
from salary_api.core.permissions import Principal, Role
from salary_api.modules.employees import service
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.schemas import EmployeeUpdate
from tests.factories import make_employee

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
