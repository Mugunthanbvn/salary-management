import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("path", ["/api/v1/openapi.json", "/api/v1/docs"])
def test_openapi_spec_and_docs_are_served_under_the_api_prefix(
    client: TestClient, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
