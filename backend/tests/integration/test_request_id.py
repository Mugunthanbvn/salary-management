import re

import pytest
from fastapi.testclient import TestClient

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def test_response_carries_a_generated_request_id_when_none_is_sent(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert UUID4.match(response.headers["X-Request-ID"])


@pytest.mark.parametrize("request_id", ["abc-123", "trace.id_42", "A" * 128])
def test_valid_incoming_request_id_is_echoed(client: TestClient, request_id: str) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": request_id})

    assert response.headers["X-Request-ID"] == request_id


@pytest.mark.parametrize(
    "request_id",
    ["has space", "semi;colon", "slash/path", "<script>", "A" * 129],
)
def test_malformed_incoming_request_id_is_replaced_with_a_new_one(
    client: TestClient, request_id: str
) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": request_id})

    assert UUID4.match(response.headers["X-Request-ID"])
