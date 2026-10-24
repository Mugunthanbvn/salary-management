"""A 10,000-row import and export stay inside their budgets (docs/19-performance.md section 2).

Slow (about 10 s), so skipped by default: `RUN_SLOW=1 uv run pytest -m slow -p no:xdist -s`.
Measured on the in-memory test database; the timings are printed for docs/19 section 9.
"""

import io
import os
from collections.abc import Callable
from time import perf_counter

import pytest
import time_machine
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal
from salary_api.core.schemas import FileFormat
from salary_api.domain.constants import MAX_IMPORT_ROWS
from salary_api.modules.exports import service as exports
from salary_api.modules.exports.schemas import EmployeeExportQuery
from salary_api.modules.imports import service as imports
from tests.factories import make_fx_rates, make_user
from tests.spreadsheets import hire, import_csv, make_import_reference

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="timing check: RUN_SLOW=1"),
]


def _timed[T](label: str, work: Callable[[], T]) -> tuple[T, float]:
    started = perf_counter()
    result = work()
    seconds = perf_counter() - started
    print(f"{label}: {seconds:.2f} s")
    return result, seconds


def test_a_10000_row_csv_dry_runs_in_5_s_commits_in_10_s_and_exports_in_3_s(
    db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    make_import_reference(db_session)
    make_fx_rates(db_session)
    user = make_user(db_session, role="HR_MANAGER")
    hr = Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=user.role)
    content = import_csv(
        *(
            hire(n, bonus_target="4160.50", allowance_1_name="Transport", allowance_1_amount="1200")
            for n in range(1, MAX_IMPORT_ROWS + 1)
        )
    )
    print(f"\n{MAX_IMPORT_ROWS} rows, {len(content) / 1e6:.2f} MB CSV")

    report, dry_run_s = _timed(
        "dry-run",
        lambda: imports.dry_run(db_session, hr, filename="all.csv", upload=io.BytesIO(content)),
    )
    result, commit_s = _timed("commit", lambda: imports.commit(db_session, hr, report.id))
    exports_s = [
        _timed(
            f"export {file_format}",
            lambda file_format=file_format: exports.export_employees(
                db_session, hr, EmployeeExportQuery(format=file_format)
            ),
        )[1]
        for file_format in FileFormat
    ]

    assert (report.valid_count, result.inserted) == (MAX_IMPORT_ROWS, MAX_IMPORT_ROWS)
    assert dry_run_s < 5
    assert commit_s < 10
    assert max(exports_s) < 3
