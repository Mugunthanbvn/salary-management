"""Viewers never receive an individual salary (docs/08-security-rbac.md section 4.1).

Masking lives in the service, because exports and the Ask tools call services directly.
"""

from collections.abc import Callable
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.errors import Forbidden
from salary_api.core.permissions import Principal, Role
from salary_api.modules.employees import service
from salary_api.modules.employees.schemas import EmployeeListQuery
from tests.factories import make_employee, make_fx_rates
from tests.integration.test_authz_matrix import MATRIX, Endpoint

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
    assert (page.items[0].version is None, detail.version is None) == (masked, masked)


SALARY_QUERIES: list[dict[str, str | int]] = [
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
    as_role: Callable[[str], TestClient], params: dict[str, str | int]
) -> None:
    response = as_role("VIEWER").get(EMPLOYEES, params=params | {"currency": "EUR"})

    assert response.status_code == 403
    assert response.json()["type"] == "https://acme.example/problems/forbidden"


@pytest.mark.parametrize("params", SALARY_QUERIES)
def test_hr_may_filter_and_sort_by_salary(
    as_role: Callable[[str], TestClient], db_session: Session, params: dict[str, str | int]
) -> None:
    make_fx_rates(db_session)  # salary_basis=usd converts with them

    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params | {"currency": "EUR"})

    assert response.status_code == 200


def test_the_service_refuses_a_salary_filter_from_a_caller_without_salary_read(
    db_session: Session,
) -> None:
    with pytest.raises(Forbidden):
        service.list_employees(
            db_session, _principal(Role.VIEWER), EmployeeListQuery(salary_min=1, currency=["EUR"])
        )


def _amounts_in(body: object, path: str = "$") -> list[str]:
    """Where a JSON body reveals individual pay, at any depth: a non-null `*_minor` member, or a
    non-null `version` (it goes up with every salary change, so it dates them)."""
    found: list[str] = []
    if isinstance(body, dict):
        for key, value in cast(dict[str, object], body).items():
            if (key.endswith("_minor") or key == "version") and value is not None:
                found.append(f"{path}.{key}")
            found += _amounts_in(value, f"{path}.{key}")
    elif isinstance(body, list):
        for index, value in enumerate(cast(list[object], body)):
            found += _amounts_in(value, f"{path}[{index}]")
    return found


EMPLOYEE_ROUTES = [row for row in MATRIX if row.path.startswith("/api/v1/employees")]


@pytest.mark.parametrize(
    "endpoint", [pytest.param(row, id=f"{row.method} {row.path}") for row in EMPLOYEE_ROUTES]
)
def test_viewer_never_receives_an_amount_from_any_employee_endpoint(
    as_role: Callable[[str], TestClient], db_session: Session, endpoint: Endpoint
) -> None:
    make_employee(db_session, components=[("BONUS_TARGET", "Target bonus", 600_000)])
    request = endpoint.prepare(db_session)
    url = request.pop("url", endpoint.path)

    response = as_role("VIEWER").request(endpoint.method, url, **request)

    if response.headers.get("content-type", "").endswith("json"):
        assert _amounts_in(response.json()) == []


def test_the_amount_scan_finds_an_amount_or_a_version_at_any_depth() -> None:
    body = {"items": [{"current_base": {"amount_minor": 1, "currency": "EUR"}, "version": 3}]}

    assert _amounts_in(body) == ["$.items[0].current_base.amount_minor", "$.items[0].version"]
