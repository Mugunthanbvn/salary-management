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
from tests.spreadsheets import hire, import_csv, import_xlsx, make_import_reference

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


def test_10000_rows_dry_run_in_5_s_commit_in_10_s_and_export_in_3_s_csv_5_s_xlsx(
    db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    make_import_reference(db_session)
    make_fx_rates(db_session)
    user = make_user(db_session, role="HR_MANAGER")
    hr = Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=user.role)
    rows = [
        hire(n, bonus_target="4160.50", allowance_1_name="Transport", allowance_1_amount="1200")
        for n in range(1, MAX_IMPORT_ROWS + 1)
    ]
    csv_file, xlsx_file = import_csv(*rows), import_xlsx(*rows)
    print(
        f"\n{len(rows)} rows: {len(csv_file) / 1e6:.2f} MB CSV, {len(xlsx_file) / 1e6:.2f} MB XLSX"
    )

    _, xlsx_dry_run_s = _timed(
        "dry-run xlsx",
        lambda: imports.dry_run(db_session, hr, filename="all.xlsx", upload=io.BytesIO(xlsx_file)),
    )
    report, dry_run_s = _timed(
        "dry-run csv",
        lambda: imports.dry_run(db_session, hr, filename="all.csv", upload=io.BytesIO(csv_file)),
    )
    result, commit_s = _timed("commit", lambda: imports.commit(db_session, hr, report.id))
    csv_export_s, xlsx_export_s = (
        _timed(
            f"export {file_format}",
            lambda file_format=file_format: exports.export_employees(
                db_session, hr, EmployeeExportQuery(format=file_format)
            ),
        )[1]
        for file_format in (FileFormat.CSV, FileFormat.XLSX)
    )

    assert (report.valid_count, result.inserted) == (MAX_IMPORT_ROWS, MAX_IMPORT_ROWS)
    assert max(dry_run_s, xlsx_dry_run_s) < 5
    assert commit_s < 10
    assert csv_export_s < 3
    assert xlsx_export_s < 5
