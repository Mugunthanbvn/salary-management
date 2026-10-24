"""Every error is RFC 9457 problem+json with a glossary slug (docs/glossary.md section 5)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from salary_api.core.errors import (
    BadRequest,
    Duplicate,
    Forbidden,
    ImportFailed,
    InvalidState,
    NotFound,
    PayloadTooLarge,
    ProblemError,
    Unauthenticated,
    UnsupportedMediaType,
    VersionConflict,
)

PROBLEM_JSON = "application/problem+json"
PROBLEMS = "https://acme.example/problems/"


def test_unknown_route_returns_404_problem_json(client: TestClient) -> None:
    response = client.get("/api/v1/no-such-route", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": f"{PROBLEMS}not-found",
        "title": "Not found",
        "status": 404,
        "instance": "/api/v1/no-such-route",
        "request_id": "req-404",
    }


def test_status_without_a_glossary_slug_uses_about_blank(client: TestClient) -> None:
    response = client.delete("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["type"] == "about:blank"
    assert response.json()["title"] == "Method Not Allowed"


def test_invalid_request_returns_422_problem_json_with_field_errors(
    app: FastAPI, client: TestClient
) -> None:
    @app.get("/api/v1/_test/items/{item_id}")
    def read_item(item_id: int, page: int = 1) -> dict[str, int]:
        return {"item_id": item_id, "page": page}

    response = client.get("/api/v1/_test/items/abc?page=x", headers={"X-Request-ID": "req-422"})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    errors = body.pop("errors")
    assert body == {
        "type": f"{PROBLEMS}validation",
        "title": "Validation failed",
        "status": 422,
        "detail": "2 fields are invalid.",
        "instance": "/api/v1/_test/items/abc",
        "request_id": "req-422",
    }
    assert [(error["loc"], error["code"]) for error in errors] == [
        (["path", "item_id"], "int_parsing"),
        (["query", "page"], "int_parsing"),
    ]
    assert all(isinstance(error["message"], str) and error["message"] for error in errors)


def test_unhandled_error_returns_500_problem_json_without_internal_detail(app: FastAPI) -> None:
    @app.get("/api/v1/_test/boom")
    def boom() -> None:
        raise RuntimeError("connection string has password hunter2")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_test/boom", headers={"X-Request-ID": "req-500"})

    assert response.status_code == 500
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["X-Request-ID"] == "req-500"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "/api/v1/_test/boom",
        "request_id": "req-500",
    }
    assert "hunter2" not in response.text


@pytest.mark.parametrize(
    ("problem", "expected"),
    [
        (Unauthenticated("Sign in to continue."), (401, "unauthenticated", "Not authenticated")),
        (Forbidden("Requires SALARY_READ."), (403, "forbidden", "Forbidden")),
        (NotFound("Employee 42 was not found."), (404, "not-found", "Not found")),
        (Duplicate("Email is already in use."), (409, "duplicate", "Duplicate")),
        (InvalidState("Employee 42 is terminated."), (409, "invalid-state", "Invalid state")),
        (BadRequest("The file is not UTF-8."), (400, "bad-request", "Bad request")),
        (PayloadTooLarge("Upload at most 4 MB."), (413, "payload-too-large", "Payload too large")),
        (
            UnsupportedMediaType("Upload a .csv or .xlsx file."),
            (415, "unsupported-media-type", "Unsupported media type"),
        ),
        (ImportFailed("Nothing was imported."), (500, "import-failed", "Import failed")),
    ],
)
def test_problem_exceptions_render_their_glossary_status_slug_and_title(
    app: FastAPI, client: TestClient, problem: ProblemError, expected: tuple[int, str, str]
) -> None:
    status, slug, title = expected

    @app.get("/api/v1/_test/problem")
    def raise_problem() -> None:
        raise problem

    response = client.get("/api/v1/_test/problem")

    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert (body["type"], body["title"], body["detail"]) == (
        f"{PROBLEMS}{slug}",
        title,
        problem.detail,
    )


def test_version_conflict_returns_409_with_the_current_version(
    app: FastAPI, client: TestClient
) -> None:
    @app.patch("/api/v1/_test/employees/42")
    def update_employee() -> None:
        raise VersionConflict("Employee 42 was modified by someone else.", current_version=8)

    response = client.patch("/api/v1/_test/employees/42")

    assert response.status_code == 409
    assert response.json()["type"] == f"{PROBLEMS}version-conflict"
    assert response.json()["current_version"] == 8


def test_invalid_response_is_logged_by_type_without_the_response_body(
    app: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    class Salary(BaseModel):
        amount_minor: int

    @app.get("/api/v1/_test/salary", response_model=Salary)
    def read_salary() -> dict[str, str]:
        return {"amount_minor": "base-salary-6500000"}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_test/salary")

    logged = capsys.readouterr().out
    assert response.status_code == 500
    assert "ResponseValidationError" in logged
    assert "base-salary-6500000" not in logged


def test_an_unexpected_error_is_logged_with_its_type_and_frames_but_not_its_message(
    app: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    @app.get("/api/v1/_test/personal")
    def personal() -> None:
        raise ValueError("Lena Müller cannot be used in worksheets.")

    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/api/v1/_test/personal", headers={"X-Request-ID": "req-log"})

    logged = capsys.readouterr().out
    assert "ValueError" in logged
    assert "req-log" in logged
    assert " in personal" in logged  # the frame where it was raised
    assert "Lena" not in logged
