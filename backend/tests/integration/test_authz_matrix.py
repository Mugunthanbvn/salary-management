"""Every endpoint, for every role: the expected status (docs/14-testing-strategy.md section 5.3).

MATRIX is the table: one row per route, with the status each caller gets.
A guard test introspects every route of the app, so a new endpoint without a row fails CI.
Statuses mirror docs/08-security-rbac.md section 3 and docs/07-api-spec.md section 2.

When you add an endpoint, add its row here. If the request needs a body, query or a
row in the database (an employee id in the path), give the row a `prepare` function.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import (
    DEFAULT_PASSWORD,
    employee_request,
    make_country,
    make_employee,
    make_job_role,
    make_user,
)

ANON = "ANON"
EMPLOYEE = "/api/v1/employees/{employee_id:int}"  # int only, so /employees/export is not an id
CALLERS = (ANON, "VIEWER", "HR_MANAGER", "ADMIN")

# Builds one call: TestClient.request keyword arguments (json, params, files, ...) plus an
# optional "url" for paths with parameters. It may create rows in the test's session.
type Prepare = Callable[[Session], dict[str, Any]]


def _no_request_data(_session: Session) -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str  # the route's path as FastAPI registers it, e.g. /api/v1/employees/{id}
    expected: tuple[int, int, int, int]  # in CALLERS order: ANON, VIEWER, HR_MANAGER, ADMIN
    prepare: Prepare = _no_request_data


def _valid_credentials(session: Session) -> dict[str, Any]:
    user = make_user(session, email="matrix-login@acme.example")
    return {"json": {"email": user.email, "password": DEFAULT_PASSWORD}}


def _new_employee(session: Session) -> dict[str, Any]:
    make_country(session, "DE")
    return {"json": employee_request(make_job_role(session).id, hire_date="2024-01-15")}


def _an_employee(session: Session) -> dict[str, Any]:
    return {"url": f"/api/v1/employees/{make_employee(session).id}"}


def _profile_change(session: Session) -> dict[str, Any]:
    employee = make_employee(session)
    return {"url": f"/api/v1/employees/{employee.id}", "json": {"version": 1, "first_name": "X"}}


def _active_employee(session: Session) -> dict[str, Any]:
    return {
        "url": f"/api/v1/employees/{make_employee(session).id}/terminate",
        "json": {"version": 1},
    }


def _terminated_employee(session: Session) -> dict[str, Any]:
    employee = make_employee(session, status="TERMINATED")
    return {"url": f"/api/v1/employees/{employee.id}/reactivate", "json": {"version": 1}}


def _salary_change(session: Session) -> dict[str, Any]:
    employee = make_employee(session, hire_date=date(2024, 1, 15))
    body = {
        "version": 1,
        "effective_date": "2024-06-01",
        "reason": "MERIT",
        "base_minor": 7_000_000,
    }
    return {"url": f"/api/v1/employees/{employee.id}/salary-changes", "json": body}


def _salary_history(session: Session) -> dict[str, Any]:
    return {"url": f"/api/v1/employees/{make_employee(session).id}/salary-history"}


MATRIX = [
    #                                          ANON VIEWER  HR  ADMIN
    Endpoint("POST", "/api/v1/auth/login", (200, 200, 200, 200), _valid_credentials),
    Endpoint("POST", "/api/v1/auth/logout", (401, 204, 204, 204)),
    Endpoint("GET", "/api/v1/auth/me", (401, 200, 200, 200)),
    Endpoint("GET", "/api/v1/reference", (401, 200, 200, 200)),
    Endpoint("GET", "/api/v1/countries", (401, 200, 200, 200)),
    Endpoint("GET", "/api/v1/employees", (401, 200, 200, 200)),
    Endpoint("POST", "/api/v1/employees", (401, 403, 201, 201), _new_employee),
    Endpoint("GET", EMPLOYEE, (401, 200, 200, 200), _an_employee),
    Endpoint("PATCH", EMPLOYEE, (401, 403, 200, 200), _profile_change),
    Endpoint("POST", f"{EMPLOYEE}/terminate", (401, 403, 200, 200), _active_employee),
    Endpoint("POST", f"{EMPLOYEE}/reactivate", (401, 403, 200, 200), _terminated_employee),
    Endpoint("POST", f"{EMPLOYEE}/salary-changes", (401, 403, 201, 201), _salary_change),
    Endpoint("GET", f"{EMPLOYEE}/salary-history", (401, 403, 200, 200), _salary_history),
]

# Routes that need no row: no permission and no data behind them. Every other route of
# the app, under /api/v1 or not, must be in MATRIX.
EXEMPT = {
    ("GET", "/api/v1/health"),  # public; tests/integration/test_health_api.py
    ("GET", "/api/v1/openapi.json"),
    ("GET", "/api/v1/docs"),
}


@pytest.mark.parametrize(
    ("endpoint", "caller"),
    [
        pytest.param(endpoint, caller, id=f"{endpoint.method} {endpoint.path} as {caller}")
        for endpoint in MATRIX
        for caller in CALLERS
    ],
)
def test_each_endpoint_returns_the_expected_status_for_each_caller(
    endpoint: Endpoint,
    caller: str,
    client: TestClient,
    as_role: Callable[[str], TestClient],
    db_session: Session,
) -> None:
    http = client if caller == ANON else as_role(caller)
    request = endpoint.prepare(db_session)
    url = request.pop("url", endpoint.path)

    response = http.request(endpoint.method, url, **request)

    assert response.status_code == endpoint.expected[CALLERS.index(caller)]


def _app_routes(app: FastAPI) -> set[tuple[str, str]]:
    """(method, path) of every route of the app, also inside included routers.

    HEAD is implied by GET.
    """
    return {
        (method, route.path)
        for route in iter_route_contexts(app.routes)
        if route.path is not None
        for method in (route.methods or set()) - {"HEAD"}
    }


def _routes_missing_from_the_matrix(app: FastAPI) -> set[tuple[str, str]]:
    listed = {(endpoint.method, endpoint.path) for endpoint in MATRIX}
    return _app_routes(app) - EXEMPT - listed


def test_every_route_is_in_the_matrix(app: FastAPI) -> None:
    assert _routes_missing_from_the_matrix(app) == set(), (
        "Add these routes to MATRIX with the status each caller should get"
    )


def test_every_matrix_row_is_a_real_route(app: FastAPI) -> None:
    listed = [(endpoint.method, endpoint.path) for endpoint in MATRIX]

    assert len(listed) == len(set(listed)), "A route is listed twice"
    assert set(listed) - _app_routes(app) == set(), (
        "Remove or fix rows for routes that do not exist"
    )


def test_the_guard_finds_a_route_missing_from_the_matrix(app: FastAPI) -> None:
    @app.get("/api/v1/_test/unlisted")
    def unlisted() -> None:
        return None

    assert _routes_missing_from_the_matrix(app) == {("GET", "/api/v1/_test/unlisted")}


def test_the_guard_finds_a_route_outside_the_api_prefix(app: FastAPI) -> None:
    @app.get("/outside-the-api")
    def outside() -> None:
        return None

    assert _routes_missing_from_the_matrix(app) == {("GET", "/outside-the-api")}
