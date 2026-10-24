"""CORS is for local development only; production is same-origin through the Next.js rewrite."""

from fastapi.testclient import TestClient

from salary_api.main import create_app
from tests.factories import make_settings

WEB_ORIGIN = "http://localhost:3000"


def test_configured_origin_may_call_the_api_with_credentials() -> None:
    app = create_app(make_settings(cors_origins=[WEB_ORIGIN]))

    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"Origin": WEB_ORIGIN})

    assert response.headers["access-control-allow-origin"] == WEB_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_no_cors_headers_are_sent_when_no_origins_are_configured(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": WEB_ORIGIN})

    assert "access-control-allow-origin" not in response.headers
