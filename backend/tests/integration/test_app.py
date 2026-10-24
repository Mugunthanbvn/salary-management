import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


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
