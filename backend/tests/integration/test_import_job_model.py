"""The import_jobs table (docs/06-data-model.md section 4.10) and its constraints."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from salary_api.domain.enums import ImportFormat, ImportStatus
from salary_api.modules.imports.models import ImportJob
from tests.conftest import FROZEN_NOW
from tests.factories import make_user


def _job_row(session: Session, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "filename": "q4-new-hires.csv",
        "format": ImportFormat.CSV,
        "status": ImportStatus.DRY_RUN,
        "file_sha256": "a" * 64,
        "row_count": 2,
        "valid_count": 2,
        "error_count": 0,
        "errors": [],
        "created_by": make_user(session, role="HR_MANAGER").id,
        "created_at": FROZEN_NOW,
        "expires_at": FROZEN_NOW + timedelta(hours=24),
    }
    return row | overrides


def test_an_import_job_keeps_its_report_and_payload(db_session: Session) -> None:
    errors = [{"row": 3, "column": "email", "code": "required", "message": "x", "value": None}]
    job = ImportJob(
        **_job_row(db_session, errors=errors, payload=[{"row": 2}], preview=[{"row": 2}])
    )
    db_session.add(job)
    db_session.flush()
    db_session.expire_all()

    stored = db_session.get(ImportJob, job.id)

    assert stored is not None
    assert (stored.status, stored.format, stored.errors, stored.payload, stored.preview) == (
        ImportStatus.DRY_RUN,
        ImportFormat.CSV,
        errors,
        [{"row": 2}],
        [{"row": 2}],
    )
    assert (stored.committed_at, stored.failure_reason) == (None, None)
    assert stored.expires_at == FROZEN_NOW + timedelta(hours=24)


@pytest.mark.parametrize(("column", "value"), [("status", "DONE"), ("format", "XLS")])
def test_the_database_rejects_an_unknown_status_or_format(
    db_session: Session, column: str, value: str
) -> None:
    row = _job_row(db_session) | {column: value}

    with pytest.raises(IntegrityError, match="CHECK"):
        db_session.execute(insert(ImportJob).values(**row))
