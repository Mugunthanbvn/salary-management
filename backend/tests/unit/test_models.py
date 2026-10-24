"""The shared UTC timestamp column type (docs/06-data-model.md section 3)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import sqlite

from salary_api.core.models import UtcDateTime

DIALECT = sqlite.dialect()
NINE_UTC = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def test_a_naive_timestamp_is_refused_on_write() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        UtcDateTime().process_bind_param(datetime(2026, 10, 1, 9, 0), DIALECT)


def test_a_timestamp_in_another_zone_is_written_as_utc() -> None:
    eleven_in_berlin = datetime(2026, 10, 1, 11, 0, tzinfo=timezone(timedelta(hours=2)))

    assert UtcDateTime().process_bind_param(eleven_in_berlin, DIALECT) == NINE_UTC


@pytest.mark.parametrize(
    "stored",
    [
        pytest.param(datetime(2026, 10, 1, 9, 0), id="naive, as SQLite returns it"),
        pytest.param(
            datetime(2026, 10, 1, 11, 0, tzinfo=timezone(timedelta(hours=2))), id="other zone"
        ),
    ],
)
def test_a_stored_timestamp_is_read_back_as_aware_utc(stored: datetime) -> None:
    read = UtcDateTime().process_result_value(stored, DIALECT)

    assert read == NINE_UTC
    assert read is not None
    assert read.tzinfo is UTC
