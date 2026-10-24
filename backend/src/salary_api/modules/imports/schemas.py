from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from salary_api.core.schemas import Money
from salary_api.domain.enums import EmploymentType, ImportFormat, ImportStatus, Level
from salary_api.modules.imports.validation import RowErrorCode


class ImportRowError(BaseModel):
    """One refused cell (docs/glossary.md section 6). `row` is the spreadsheet row number
    (the header is row 1); `value` is the cell as written, null when it was empty."""

    row: int
    column: str
    code: RowErrorCode
    message: str
    value: str | None


class ImportPreviewRow(BaseModel):
    """A valid row as it will be imported. The department follows from the job role."""

    row: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    job_role: str
    department: str
    level: Level
    employment_type: EmploymentType
    country_code: str
    hire_date: date
    salary_effective_date: date
    base: Money
    total: Money


class ImportJobReport(BaseModel):
    """A dry-run report. `valid_count` rows have no error; `error_count` counts every error
    (one row can have several), of which `errors` lists the first 500. Only a DRY_RUN job
    without errors can be committed, until `expires_at`."""

    id: int
    status: ImportStatus
    format: ImportFormat
    filename: str
    row_count: int
    valid_count: int
    error_count: int
    errors: list[ImportRowError]  # the first 500, in row order
    errors_truncated: bool  # true when error_count is more than the errors listed
    # The valid values of each column with an unknown_value error, e.g. {"level": ["L1", ...]}.
    allowed_values: dict[str, list[str]]
    preview: list[ImportPreviewRow]  # the first 50 valid rows; empty once the job has ended
    created_at: datetime
    expires_at: datetime
    committed_at: datetime | None


class ImportCommitResult(BaseModel):
    id: int
    status: Literal[ImportStatus.COMMITTED]
    inserted: int  # employees created, each with a HIRE salary record
