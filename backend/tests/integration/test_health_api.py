from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from salary_api import __version__
from salary_api.core.deps import get_session


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "version": __version__}


def test_health_returns_503_problem_json_when_the_database_is_unreachable(
    app: FastAPI, tmp_path: Path
) -> None:
    unreachable = create_engine(f"sqlite:///{tmp_path / 'no-such-dir' / 'app.db'}")

    def unreachable_session() -> Iterator[Session]:
        with Session(unreachable) as session:
            yield session

    app.dependency_overrides[get_session] = unreachable_session

    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "req-503"})

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The database is not reachable.",
        "instance": "/api/v1/health",
        "request_id": "req-503",
        "db": "error",
    }
