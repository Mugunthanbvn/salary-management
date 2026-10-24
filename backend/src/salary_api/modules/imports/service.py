"""Bulk import use cases: dry-run an upload, show a job, commit it (docs/11-import-export.md).

Each public function is one transaction. The dry-run writes nothing but its import job and
the `import.dry_run` audit event.
"""

import hashlib
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import IO, Any, Final

import structlog
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from salary_api.core.errors import (
    BadRequest,
    Duplicate,
    ImportFailed,
    InvalidState,
    NotFound,
    PayloadTooLarge,
    UnsupportedMediaType,
    ValidationFailed,
)
from salary_api.core.models import utc_now
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import Money
from salary_api.domain.constants import (
    DRY_RUN_TTL,
    MAX_ACTIVE_DRY_RUNS,
    MAX_IMPORT_ROWS,
    MAX_UPLOAD_BYTES,
    MAX_XLSX_UNCOMPRESSED_BYTES,
)
from salary_api.domain.enums import EmploymentType, ImportFormat, ImportStatus, Level
from salary_api.domain.money import Money as DomainMoney
from salary_api.modules.audit.service import AuditAction, record_event
from salary_api.modules.employees import service as employees
from salary_api.modules.imports import repository
from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.imports.models import ImportJob
from salary_api.modules.imports.parsing import (
    HeaderMismatch,
    RawRow,
    TooManyRows,
    UnreadableFile,
    parse_csv,
    parse_xlsx,
)
from salary_api.modules.imports.schemas import (
    ImportCommitResult,
    ImportJobReport,
    ImportPreviewRow,
    ImportRowError,
)
from salary_api.modules.imports.validation import (
    ImportReference,
    ImportRow,
    KnownCountry,
    KnownJobRole,
    RowError,
    RowKey,
    db_duplicates,
    mark_db_duplicates,
    validate_rows,
)
from salary_api.modules.reference import repository as reference
from salary_api.modules.salaries import service as salaries
from salary_api.modules.salaries.schemas import ComponentIn

_logger = structlog.get_logger(__name__)

ENTITY = "import_job"  # audit events name the entity they change
PREVIEW_ROWS: Final = 50
FORMATS: Final = {".csv": ImportFormat.CSV, ".xlsx": ImportFormat.XLSX}
MAX_FILENAME = 255


def dry_run(
    session: Session, principal: Principal, *, filename: str | None, upload: IO[bytes]
) -> ImportJobReport:
    """Parse, validate and duplicate-check an upload, and store the report as a DRY_RUN job.

    A file with row errors is still a dry-run (its errors are the report); an unreadable
    file is BadRequest, a wrong type UnsupportedMediaType, a big one PayloadTooLarge.
    """
    import_format = _format_of(filename)
    content = upload.read(MAX_UPLOAD_BYTES + 1)  # one byte more tells a file over the cap
    if len(content) > MAX_UPLOAD_BYTES:
        raise PayloadTooLarge(f"Upload at most {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    report = validate_rows(_parse(import_format, content), _reference(session))
    report = mark_db_duplicates(
        report,
        taken_codes=repository.codes_in_use(session, report.employee_codes),
        taken_emails=repository.emails_in_use(session, report.emails),
    )
    now = utc_now()
    repository.expire_stale(session, now)
    _make_room_for_a_dry_run(session, principal.user_id)
    job = ImportJob(
        filename=_display_name(filename),
        format=import_format,
        status=ImportStatus.DRY_RUN,
        file_sha256=hashlib.sha256(content).hexdigest(),
        row_count=report.row_count,
        valid_count=len(report.rows),
        error_count=len(report.errors),
        errors=[_error_json(error) for error in report.errors],
        preview=[_preview(row).model_dump(mode="json") for row in report.rows[:PREVIEW_ROWS]],
        # Only a report without errors can be committed, so only then are the rows kept.
        payload=None if report.errors else [_payload_row(row) for row in report.rows],
        created_by=principal.user_id,
        created_at=now,
        expires_at=now + DRY_RUN_TTL,
    )
    repository.add(session, job)
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.IMPORT_DRY_RUN,
        entity=ENTITY,
        entity_id=job.id,
        diff={
            "job_id": job.id,
            "filename": job.filename,
            "format": job.format,
            "file_sha256": job.file_sha256,
            "row_count": job.row_count,
            "valid_count": job.valid_count,
            "error_count": job.error_count,
        },
    )
    session.commit()
    return _job_report(job, now)


def get_job(session: Session, principal: Principal, job_id: int) -> ImportJobReport:
    """The job's report, for its creator or an administrator (NotFound for anyone else)."""
    return _job_report(_visible_job(session, principal, job_id), utc_now())


def commit(session: Session, principal: Principal, job_id: int) -> ImportCommitResult:
    """Create every employee of an error-free dry-run in one transaction, or none.

    Refused (InvalidState) unless the job is a DRY_RUN without errors and not expired; an
    expired one is stored as EXPIRED. Codes and emails are checked against the employees
    again (Duplicate lists the rows taken since the dry-run). Any other failure rolls back
    everything, marks the job FAILED in a transaction of its own, and raises ImportFailed.
    """
    job = _visible_job(session, principal, job_id)
    now = utc_now()
    _require_committable(session, job, now)
    payload = job.payload or []
    conflicts = db_duplicates(
        [RowKey(row["row"], row["employee_code"], row["email"]) for row in payload],
        taken_codes=repository.codes_in_use(session, [row["employee_code"] for row in payload]),
        taken_emails=repository.emails_in_use(session, [row["email"] for row in payload]),
    )
    if conflicts:
        raise Duplicate(
            "Employees added since the dry-run use some codes or emails of this file "
            "(see conflicts). Nothing was imported: fix the file and upload it again.",
            conflicts=[_error_json(error) for error in conflicts],
        )
    codes = sorted(row["employee_code"] for row in payload)
    try:
        employees.add_hires_in_bulk(
            session, [_new_hire(row) for row in payload], changed_by=principal.user_id
        )
        record_event(
            session,
            actor_id=principal.user_id,
            action=AuditAction.IMPORT_COMMIT,
            entity=ENTITY,
            entity_id=job.id,
            diff={
                "job_id": job.id,
                "inserted": len(codes),
                "employee_code_range": [codes[0], codes[-1]],
            },
        )
        job.committed_at = now
        _end(job, ImportStatus.COMMITTED)
        session.commit()
    except Exception as error:  # any failure: roll back, then record it
        session.rollback()
        _record_failure(session, principal, job_id, error)
        raise ImportFailed(
            f"Import {job_id} failed and nothing was written. Upload the file again to retry.",
            job_id=job_id,
        ) from None
    return ImportCommitResult(id=job_id, status=ImportStatus.COMMITTED, inserted=len(codes))


_NOT_COMMITTABLE: Final = {
    ImportStatus.COMMITTED: "This import was already committed.",
    ImportStatus.FAILED: "This import failed. Upload the file again to retry.",
    ImportStatus.EXPIRED: "This dry-run has expired. Upload the file again.",
}


def _require_committable(session: Session, job: ImportJob, now: datetime) -> None:
    if job.status != ImportStatus.DRY_RUN:
        raise InvalidState(_NOT_COMMITTABLE[job.status])
    if job.error_count:
        raise InvalidState("This dry-run has errors: fix the file and upload it again.")
    if now >= job.expires_at:
        _end(job, ImportStatus.EXPIRED)
        session.commit()
        raise InvalidState("This dry-run expired 24 hours after the upload. Upload the file again.")


def _record_failure(session: Session, principal: Principal, job_id: int, error: Exception) -> None:
    """Mark the job FAILED and write import.fail, after the rollback (its own transaction)."""
    reason = _failure_reason(error)
    _logger.error("import_commit_failed", job_id=job_id, error_type=type(error).__name__)
    job = repository.get(session, job_id)
    if job is None:  # pragma: no cover  (the job was read in this request)
        return
    job.failure_reason = reason
    _end(job, ImportStatus.FAILED)
    record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.IMPORT_FAIL,
        entity=ENTITY,
        entity_id=job_id,
        diff={"job_id": job_id, "failure_reason": reason},
    )
    session.commit()


def _failure_reason(error: Exception) -> str:
    """The error type, and for a database error its message (bound values are hidden by the
    engine), so the reason never holds row data such as salaries."""
    if isinstance(error, DBAPIError):
        return f"{type(error).__name__}: {str(error.orig).splitlines()[0]}"[:500]
    return type(error).__name__


def _new_hire(row: Mapping[str, Any]) -> employees.NewHire:
    """A payload row (stored at the dry-run) as a new employee with their first salary."""
    return employees.NewHire(
        employee_code=row["employee_code"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        job_role_id=row["job_role_id"],
        level=Level(row["level"]),
        employment_type=EmploymentType(row["employment_type"]),
        country_code=row["country_code"],
        hire_date=date.fromisoformat(row["hire_date"]),
        salary_effective_date=date.fromisoformat(row["salary_effective_date"]),
        pay=salaries.Pay(
            base=DomainMoney(row["base_minor"], row["currency"]),
            components=[ComponentIn.model_validate(c) for c in row["components"]],
        ),
    )


def _visible_job(session: Session, principal: Principal, job_id: int) -> ImportJob:
    """The job, if the caller uploaded it or holds USER_ADMIN, the administrator's
    permission. Anyone else is told it does not exist (docs/glossary.md section 5)."""
    job = repository.get(session, job_id)
    if job is None or (
        job.created_by != principal.user_id and not principal.has(Permission.USER_ADMIN)
    ):
        raise NotFound(f"Import {job_id} was not found.")
    return job


def _format_of(filename: str | None) -> ImportFormat:
    """The format the file name's extension says; the parser then checks the content."""
    suffix = PurePosixPath(_display_name(filename)).suffix.lower()
    if suffix not in FORMATS:
        raise UnsupportedMediaType(
            "Upload a .csv or .xlsx file. Macro-enabled (.xlsm) and old (.xls) workbooks "
            "are not accepted."
        )
    return FORMATS[suffix]


def _display_name(filename: str | None) -> str:
    """The file's own name, without any folder a browser sent: shown, never used as a path."""
    return (filename or "").replace("\\", "/").rsplit("/", 1)[-1][:MAX_FILENAME]


def _parse(import_format: ImportFormat, content: bytes) -> list[RawRow]:
    try:
        if import_format == ImportFormat.CSV:
            return parse_csv(content, max_rows=MAX_IMPORT_ROWS)
        return parse_xlsx(
            content, max_rows=MAX_IMPORT_ROWS, max_uncompressed_bytes=MAX_XLSX_UNCOMPRESSED_BYTES
        )
    except HeaderMismatch as error:
        raise BadRequest(str(error), expected_headers=list(TEMPLATE_COLUMNS)) from None
    except UnreadableFile as error:
        raise BadRequest(str(error)) from None
    except TooManyRows as error:
        raise ValidationFailed(
            [{"loc": ["body", "file"], "code": "too_many_rows", "message": str(error)}]
        ) from None


def _reference(session: Session) -> ImportReference:
    """Countries and job roles, loaded once for the whole file."""
    departments = {
        department.id: department.name for department in reference.list_departments(session)
    }
    return ImportReference(
        countries={
            country.code: KnownCountry(
                code=country.code,
                name=country.name,
                currency=country.default_currency,
                is_active=country.is_active,
            )
            for country in reference.list_countries(session)
        },
        job_roles=[
            KnownJobRole(id=role.id, title=role.title, department=departments[role.department_id])
            for role in reference.list_job_roles(session)
        ],
        today=utc_now().date(),
    )


def _make_room_for_a_dry_run(session: Session, user_id: int) -> None:
    """Expire the user's oldest open dry-runs, so the new one makes MAX_ACTIVE_DRY_RUNS."""
    open_jobs = repository.open_dry_runs(session, user_id)
    for job in open_jobs[: max(0, len(open_jobs) - MAX_ACTIVE_DRY_RUNS + 1)]:
        _end(job, ImportStatus.EXPIRED)


def _end(job: ImportJob, status: ImportStatus) -> None:
    """The job is over: drop its rows, which hold salary data (docs/11 section 5.7)."""
    job.status = status
    job.payload = None
    job.preview = None


def _shown_status(job: ImportJob, now: datetime) -> ImportStatus:
    """A DRY_RUN past its expiry shows as EXPIRED, without a write in a read."""
    if job.status == ImportStatus.DRY_RUN and now >= job.expires_at:
        return ImportStatus.EXPIRED
    return job.status


def _job_report(job: ImportJob, now: datetime) -> ImportJobReport:
    return ImportJobReport(
        id=job.id,
        status=_shown_status(job, now),
        format=job.format,
        filename=job.filename,
        row_count=job.row_count,
        valid_count=job.valid_count,
        error_count=job.error_count,
        errors=[ImportRowError.model_validate(error) for error in job.errors],
        preview=[ImportPreviewRow.model_validate(row) for row in job.preview or []],
        created_at=job.created_at,
        expires_at=job.expires_at,
        committed_at=job.committed_at,
    )


def _error_json(error: RowError) -> dict[str, Any]:
    return {
        "row": error.row,
        "column": error.column,
        "code": error.code,
        "message": error.message,
        "value": error.value,
    }


def _preview(row: ImportRow) -> ImportPreviewRow:
    return ImportPreviewRow(
        row=row.row,
        employee_code=row.employee_code,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        job_role=row.job_role.title,
        department=row.job_role.department,
        level=row.level,
        employment_type=row.employment_type,
        country_code=row.country_code,
        hire_date=row.hire_date,
        salary_effective_date=row.salary_effective_date,
        base=Money(amount_minor=row.base_minor, currency=row.currency),
        total=Money(amount_minor=row.total_minor, currency=row.currency),
    )


def _payload_row(row: ImportRow) -> dict[str, Any]:
    """A validated row as stored until the commit: ids, enums and minor units only."""
    return {
        "row": row.row,
        "employee_code": row.employee_code,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "email": row.email,
        "job_role_id": row.job_role.id,
        "level": row.level,
        "employment_type": row.employment_type,
        "country_code": row.country_code,
        "currency": row.currency,
        "hire_date": row.hire_date.isoformat(),
        "salary_effective_date": row.salary_effective_date.isoformat(),
        "base_minor": row.base_minor,
        "components": [component.model_dump(mode="json") for component in row.components],
    }
