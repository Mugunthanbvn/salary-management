import json
from collections.abc import Iterator

import pytest
import structlog
import time_machine

from salary_api.core.logging import configure_logging


@pytest.fixture(autouse=True)
def _restore_structlog() -> Iterator[None]:
    yield
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


def test_log_lines_are_json_with_level_utc_timestamp_and_context(
    capsys: pytest.CaptureFixture[str], frozen_time: time_machine.Traveller
) -> None:
    configure_logging("INFO")
    structlog.contextvars.bind_contextvars(request_id="req-7")

    structlog.get_logger().info("employee_updated", employee_id=42)

    assert json.loads(capsys.readouterr().out) == {
        "event": "employee_updated",
        "employee_id": 42,
        "level": "info",
        "request_id": "req-7",
        "timestamp": "2026-10-01T09:00:00Z",
    }


def test_lines_below_the_configured_level_are_dropped(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING")

    structlog.get_logger().info("not_shown")

    assert capsys.readouterr().out == ""
