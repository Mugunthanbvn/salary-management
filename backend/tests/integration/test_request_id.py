import re

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

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


def test_log_lines_written_during_a_request_carry_its_request_id(
    app: FastAPI, client: TestClient
) -> None:
    @app.get("/api/v1/_test/log")
    def write_a_log_line() -> dict[str, str]:
        structlog.get_logger().info("inside_request")
        return {}

    with capture_logs(processors=[merge_contextvars]) as logs:
        client.get("/api/v1/_test/log", headers={"X-Request-ID": "req-42"})

    assert {"event": "inside_request", "log_level": "info", "request_id": "req-42"} in logs
