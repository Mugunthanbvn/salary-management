from fastapi.testclient import TestClient

from salary_api import __version__


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "version": __version__}
