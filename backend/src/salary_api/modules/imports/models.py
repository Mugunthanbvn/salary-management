"""The import_jobs table (docs/06-data-model.md section 4.10).

A dry-run report waits here between the upload and the commit, because serverless
functions keep nothing in memory between two requests (ADR 0012).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, JSON, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from salary_api.core.models import Base, UtcDateTime
from salary_api.domain.enums import ImportFormat, ImportStatus


class ImportJob(Base):
    """One uploaded file: its dry-run report, and the validated rows until the job ends.

    `payload` and `preview` hold salary data, so they are cleared as soon as the job is
    COMMITTED, FAILED or EXPIRED (docs/11-import-export.md section 5.7).
    """

    __tablename__ = "import_jobs"
    __table_args__ = (
        # The open dry-runs of one user (MAX_ACTIVE_DRY_RUNS).
        Index("ix_import_jobs_created_by_status", "created_by", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))  # for display only, never a path
    format: Mapped[ImportFormat] = mapped_column(
        Enum(ImportFormat, name="format", native_enum=False, create_constraint=True, length=4)
    )
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="status", native_enum=False, create_constraint=True, length=10)
    )
    file_sha256: Mapped[str] = mapped_column(CHAR(64))
    row_count: Mapped[int]
    valid_count: Mapped[int]
    error_count: Mapped[int]
    # [{row, column, code, message, value}], in row order.
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    # The first valid rows, as the UI shows them.
    preview: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    # Every normalized row; kept only while a job without errors can still be committed.
    payload: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    committed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    failure_reason: Mapped[str | None] = mapped_column(Text)
