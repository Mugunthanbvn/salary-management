from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from salary_api.core.deps import require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission


@pytest.mark.parametrize("path", ["/api/v1/openapi.json", "/api/v1/docs"])
def test_openapi_spec_and_docs_are_served_under_the_api_prefix(
    client: TestClient, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200


def test_openapi_documents_422_as_a_validation_problem_in_problem_json(app: FastAPI) -> None:
    @app.get("/api/v1/_test/items/{item_id}")
    def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    responses = app.openapi()["paths"]["/api/v1/_test/items/{item_id}"]["get"]["responses"]

    assert responses["422"]["content"] == {
        "application/problem+json": {"schema": {"$ref": "#/components/schemas/ValidationProblem"}}
    }


PROBLEM_CONTENT = {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}


def _responses(app: FastAPI, method: str, path: str) -> dict[str, Any]:
    return app.openapi()["paths"][path][method]["responses"]


def test_openapi_documents_login_401_and_429_as_problems(app: FastAPI) -> None:
    responses = _responses(app, "post", "/api/v1/auth/login")

    assert responses["401"]["content"] == PROBLEM_CONTENT
    assert responses["429"]["content"] == PROBLEM_CONTENT
    assert responses["429"]["headers"]["Retry-After"]["schema"] == {"type": "integer"}


@pytest.mark.parametrize(
    ("method", "path"), [("post", "/api/v1/auth/logout"), ("get", "/api/v1/auth/me")]
)
def test_openapi_documents_401_on_routes_that_need_a_session(
    app: FastAPI, method: str, path: str
) -> None:
    assert _responses(app, method, path)["401"]["content"] == PROBLEM_CONTENT


def test_openapi_documents_403_on_routes_that_need_a_permission(app: FastAPI) -> None:
    @app.get(
        "/api/v1/_test/salaries",
        dependencies=[Depends(require_permission(Permission.SALARY_READ))],
        responses=problem_responses(401, 403),
    )
    def salaries() -> None:
        return None

    responses = _responses(app, "get", "/api/v1/_test/salaries")

    assert responses["403"]["content"] == PROBLEM_CONTENT
    assert responses["401"]["content"] == PROBLEM_CONTENT


def test_openapi_documents_the_session_cookie_and_bearer_token(app: FastAPI) -> None:
    document = app.openapi()

    assert set(document["components"]["securitySchemes"]) == {"SessionCookie", "BearerToken"}
    assert document["paths"]["/api/v1/auth/me"]["get"]["security"] == [
        {"SessionCookie": []},
        {"BearerToken": []},
    ]


PUBLIC_OR_SESSION_ONLY = {
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/me",
}


def _operations(app: FastAPI) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (method, path, operation["responses"])
        for path, item in app.openapi()["paths"].items()
        for method, operation in item.items()
    ]


def test_openapi_documents_401_and_403_on_every_route_that_needs_a_permission(
    app: FastAPI,
) -> None:
    missing = [
        f"{method.upper()} {path}"
        for method, path, responses in _operations(app)
        if path not in PUBLIC_OR_SESSION_ONLY and not {"401", "403"} <= set(responses)
    ]

    assert missing == []


def test_openapi_documents_404_on_every_route_with_an_employee_id(app: FastAPI) -> None:
    missing = [
        f"{method.upper()} {path}"
        for method, path, responses in _operations(app)
        if "{employee_id}" in path and "404" not in responses
    ]

    assert missing == []


def test_openapi_documents_409_on_every_change_to_an_employee(app: FastAPI) -> None:
    missing = [
        f"{method.upper()} {path}"
        for method, path, responses in _operations(app)
        if path.startswith("/api/v1/employees") and method != "get" and "409" not in responses
    ]

    assert missing == []
