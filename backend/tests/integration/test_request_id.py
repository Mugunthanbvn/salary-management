import re

from fastapi.testclient import TestClient

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def test_response_carries_a_generated_request_id_when_none_is_sent(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert UUID4.match(response.headers["X-Request-ID"])
