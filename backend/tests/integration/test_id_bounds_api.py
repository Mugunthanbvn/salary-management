"""Ids and pages are bounded, so no value overflows a 64-bit SQLite integer (a 500 before).

An id above 2**63 - 1 (or below 1) is a 422, in a query, a body or a path.
"""

from collections.abc import Callable
from typing import Any

import pytest
import time_machine
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.schemas import MAX_PAGE
from tests.factories import employee_request, make_country, make_employee, make_job_role

EMPLOYEES = "/api/v1/employees"
TOO_BIG = 10**20


@pytest.mark.parametrize(
    "params",
    [
        {"page": 10**19},
        {"department_id": TOO_BIG},
        {"job_role_id": TOO_BIG},
        {"department_id": 0},
    ],
    ids=["page", "department", "job role", "id 0"],
)
def test_list_refuses_a_page_or_id_outside_64_bit_integers(
    as_role: Callable[[str], TestClient], params: dict[str, int]
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params)

    assert response.status_code == 422


def test_the_last_allowed_page_is_simply_empty(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"page": MAX_PAGE, "page_size": 100})

    assert (response.status_code, response.json()["items"]) == (200, [])


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("GET", "", None),
        ("PATCH", "", {"version": 1}),
        ("POST", "/terminate", {"version": 1}),
        ("GET", "/salary-history", None),
    ],
)
def test_an_employee_id_outside_64_bit_integers_is_422(
    as_role: Callable[[str], TestClient], method: str, suffix: str, body: dict[str, Any] | None
) -> None:
    response = as_role("HR_MANAGER").request(method, f"{EMPLOYEES}/{TOO_BIG}{suffix}", json=body)

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["path", "employee_id"]


def test_create_refuses_a_job_role_id_outside_64_bit_integers(
    as_role: Callable[[str], TestClient], db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    make_country(db_session, "DE")

    response = as_role("HR_MANAGER").post(EMPLOYEES, json=employee_request(TOO_BIG))

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", "job_role_id"]


def test_a_salary_change_refuses_a_job_role_id_outside_64_bit_integers(
    as_role: Callable[[str], TestClient], db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    employee = make_employee(db_session, job_role=make_job_role(db_session))
    body = {
        "version": 1,
        "effective_date": "2026-10-01",
        "reason": "PROMOTION",
        "job_role_id": TOO_BIG,
        "base_minor": 7_000_000,
    }

    response = as_role("HR_MANAGER").post(f"{EMPLOYEES}/{employee.id}/salary-changes", json=body)

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", "job_role_id"]
