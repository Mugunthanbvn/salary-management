"""Viewers never receive an individual salary (docs/08-security-rbac.md section 4.1).

Masking lives in the service, because exports and the Ask tools call services directly.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.errors import Forbidden
from salary_api.core.permissions import Principal, Role
from salary_api.modules.employees import service
from salary_api.modules.employees.schemas import EmployeeListQuery
from tests.factories import make_employee

EMPLOYEES = "/api/v1/employees"


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, email="caller@acme.example", full_name="Caller", role=role)


def test_viewer_cannot_see_individual_salary_in_the_list(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_employee(db_session, components=[("ALLOWANCE", "Transport", 60_000)])

    item = as_role("VIEWER").get(EMPLOYEES).json()["items"][0]

    assert (item["current_base"], item["current_total"], item["salary_masked"]) == (
        None,
        None,
        True,
    )


def test_viewer_cannot_see_individual_salary_in_the_detail(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session, components=[("ALLOWANCE", "Transport", 60_000)])

    body = as_role("VIEWER").get(f"{EMPLOYEES}/{employee.id}").json()

    assert body["salary_masked"] is True
    assert (body["current_base"], body["current_total"], body["current_salary"]) == (
        None,
        None,
        None,
    )
    assert body["last_name"] == employee.last_name  # the profile is still there


@pytest.mark.parametrize(("role", "masked"), [(Role.VIEWER, True), (Role.HR_MANAGER, False)])
def test_the_service_masks_salaries_for_callers_without_salary_read(
    db_session: Session, role: Role, masked: bool
) -> None:
    employee = make_employee(db_session)

    page = service.list_employees(db_session, _principal(role), EmployeeListQuery())
    detail = service.get_employee(db_session, _principal(role), employee.id)

    assert (page.items[0].current_base is None, page.items[0].salary_masked) == (masked, masked)
    assert (detail.current_salary is None, detail.salary_masked) == (masked, masked)


SALARY_QUERIES = [
    {"salary_min": 1},
    {"salary_max": 9_000_000},
    {"salary_basis": "usd"},
    {"comp": "total"},
    {"sort": "current_base"},
    {"sort": "-current_total"},
    {"sort": "last_name,-current_base"},
]


@pytest.mark.parametrize("params", SALARY_QUERIES)
def test_viewer_cannot_filter_or_sort_by_salary(
    as_role: Callable[[str], TestClient], params: dict[str, object]
) -> None:
    response = as_role("VIEWER").get(EMPLOYEES, params=params | {"currency": "EUR"})

    assert response.status_code == 403
    assert response.json()["type"] == "https://acme.example/problems/forbidden"


@pytest.mark.parametrize("params", SALARY_QUERIES)
def test_hr_may_filter_and_sort_by_salary(
    as_role: Callable[[str], TestClient], params: dict[str, object]
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params | {"currency": "EUR"})

    assert response.status_code == 200


def test_the_service_refuses_a_salary_filter_from_a_caller_without_salary_read(
    db_session: Session,
) -> None:
    with pytest.raises(Forbidden):
        service.list_employees(
            db_session, _principal(Role.VIEWER), EmployeeListQuery(salary_min=1, currency=["EUR"])
        )
