from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from salary_api.core.schemas import Money
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level, SalaryReason
from salary_api.modules.reference.schemas import CountryCode, CurrencyCode, Department, JobRoleRef
from salary_api.modules.salaries.schemas import BaseMinor, Component, Components, Note

EmployeeCode = Annotated[str, StringConstraints(pattern=r"^ACME-[0-9]{6}$")]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# Stored trimmed and lowercased, so uniqueness ignores case (docs/06-data-model.md 4.5).
WorkEmail = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$"
    ),
]


class HireSalary(BaseModel):
    """The first salary. `currency` may be left out: it is always the country's currency."""

    model_config = ConfigDict(extra="forbid")

    currency: CurrencyCode | None = None
    base_minor: BaseMinor
    components: Components = []
    note: Note | None = None


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_code: EmployeeCode | None = None  # generated when left out
    first_name: PersonName
    last_name: PersonName
    email: WorkEmail
    job_role_id: int
    level: Level
    employment_type: EmploymentType
    country_code: CountryCode
    hire_date: date
    salary: HireSalary


class EmployeeListItem(BaseModel):
    """An employee in a list. Without SALARY_READ the salary fields are null and
    `salary_masked` is true (docs/07-api-spec.md section 1.7)."""

    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    job_role: JobRoleRef
    department: Department
    level: Level
    employment_type: EmploymentType
    country_code: str
    status: EmployeeStatus
    hire_date: date
    current_base: Money | None
    current_total: Money | None
    salary_masked: bool
    version: int


class CurrentSalary(BaseModel):
    """The salary record the current salary comes from."""

    id: int
    effective_date: date
    reason: SalaryReason
    components: list[Component]


class EmployeeDetail(EmployeeListItem):
    termination_date: date | None
    current_salary: CurrentSalary | None
