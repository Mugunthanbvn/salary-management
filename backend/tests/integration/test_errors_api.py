"""Every error is RFC 9457 problem+json with a glossary slug (docs/glossary.md section 5)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
