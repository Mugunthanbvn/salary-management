"""PATCH /employees/{id}: profile fields only, with optimistic locking (docs/07-api-spec.md 6.4)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.modules.employees.models import Employee
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
