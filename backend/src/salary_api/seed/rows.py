"""The rows the seed writes, one dataclass per table. Field names are the column names.

Every ID is set here, in generation order, so the loader inserts in bulk without asking the
database for keys, and the same seed always gives the same IDs.
"""

from dataclasses import dataclass
from datetime import date, datetime

from salary_api.core.permissions import Role
from salary_api.domain.enums import (
    ComponentType,
    EmployeeStatus,
    EmploymentType,
    Level,
    SalaryReason,
)
from salary_api.modules.reference.models import JobFamily


@dataclass(frozen=True, slots=True)
class CountryRow:
    code: str
    name: str
    default_currency: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class DepartmentRow:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class JobRoleRow:
    id: int
    title: str
    department_id: int
    family: JobFamily


@dataclass(frozen=True, slots=True)
class PayBandRow:
    id: int
    job_role_id: int
    level: Level
    country_code: str
    currency: str
    min_minor: int
    mid_minor: int
    max_minor: int
    effective_from: date


@dataclass(frozen=True, slots=True)
class FxRateRow:
    currency: str
    rate_to_usd: str  # a decimal string, as stored
    as_of: date
    source: str
    updated_at: datetime
    updated_by: int | None = None


@dataclass(frozen=True, slots=True)
class EmployeeRow:
    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    search_text: str
    job_role_id: int
    level: Level
    employment_type: EmploymentType
    country_code: str
    status: EmployeeStatus
    hire_date: date
    termination_date: date | None
    currency: str
    current_base_minor: int
    current_total_minor: int
    # Set by the loader after the salary records exist (the two tables reference each other).
    current_salary_record_id: int
    created_at: datetime
    updated_at: datetime
    version: int = 1


@dataclass(frozen=True, slots=True)
class SalaryRecordRow:
    id: int
    employee_id: int
    effective_date: date
    currency: str
    base_minor: int
    total_minor: int
    job_role_id: int
    level: Level
    reason: SalaryReason
    created_at: datetime
    note: str | None = None
    changed_by: int | None = None  # seeded history has no acting user


@dataclass(frozen=True, slots=True)
class SalaryComponentRow:
    id: int
    salary_record_id: int
    type: ComponentType
    name: str
    amount_minor: int


@dataclass(frozen=True, slots=True)
class UserRow:
    id: int
    email: str
    full_name: str
    password_hash: str  # argon2; the password itself is never stored
    role: Role
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    last_login_at: datetime | None = None
