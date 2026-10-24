"""Every error is RFC 9457 problem+json with a glossary slug (docs/glossary.md section 5)."""

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
