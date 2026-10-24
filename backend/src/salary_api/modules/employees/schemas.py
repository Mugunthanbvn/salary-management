from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from pydantic.json_schema import SkipJsonSchema

from salary_api.core.schemas import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE,
    MAX_PAGE_SIZE,
    Comp,
    Id,
    Money,
    SalaryBasis,
)
from salary_api.domain.constants import MAX_AMOUNT_MINOR
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


SearchTerm = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


# A query parameter, so it arrives as text; "1.5" is still refused.
SalaryBound = Annotated[int, Field(ge=0, le=MAX_AMOUNT_MINOR)]


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
    job_role_id: Id
    level: Level
    employment_type: EmploymentType
    country_code: CountryCode
    hire_date: date
    salary: HireSalary


class EmployeeUpdate(BaseModel):
    """Profile fields only. Salary, role, level and country change through a salary change,
    so history explains them; they are refused here as unknown fields."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)  # the version the client read; 409 if it is no longer current
    # Leave a field out to keep it. null is refused, and the schema does not offer it.
    first_name: PersonName | SkipJsonSchema[None] = None
    last_name: PersonName | SkipJsonSchema[None] = None
    email: WorkEmail | SkipJsonSchema[None] = None
    employment_type: EmploymentType | SkipJsonSchema[None] = None

    @field_validator("first_name", "last_name", "email", "employment_type", mode="before")
    @classmethod
    def _not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Leave the field out to keep its value; it cannot be null.")
        return value


class TerminateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    termination_date: date | None = None  # today when left out; never before the hire date
    note: Note | None = None  # kept in the audit event


class ReactivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


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
    # Needed to change the employee. Null without SALARY_READ: it goes up with every salary
    # change, so it would tell when someone's pay changed (such callers cannot write anyway).
    version: int | None


class CurrentSalary(BaseModel):
    """The salary record the current salary comes from."""

    id: int
    effective_date: date
    reason: SalaryReason
    components: list[Component]


class EmployeeDetail(EmployeeListItem):
    termination_date: date | None
    current_salary: CurrentSalary | None


class EmployeeListQuery(BaseModel):
    """The query of GET /employees. Unknown parameters are refused (422), so typos show."""

    model_config = ConfigDict(extra="forbid")

    # Repeat a key for several values (?country=DE&country=FR): values of one key are ORed,
    # different keys are ANDed.
    # Name, employee code or email; accents and case are ignored (docs/06 section 6.4).
    q: SearchTerm | None = None
    country: list[CountryCode] = Field(default_factory=list[CountryCode])
    department_id: list[Id] = Field(default_factory=list[Id])
    job_role_id: list[Id] = Field(default_factory=list[Id])
    level: list[Level] = Field(default_factory=list[Level])
    employment_type: list[EmploymentType] = Field(default_factory=list[EmploymentType])
    status: list[EmployeeStatus] = Field(default_factory=lambda: [EmployeeStatus.ACTIVE])
    currency: list[CurrencyCode] = Field(default_factory=list[CurrencyCode])
    # Salary range in minor units. These, salary_basis, comp and the salary sorts need
    # SALARY_READ (403 otherwise): repeated range queries could isolate one person's pay.
    salary_min: SalaryBound | None = None
    salary_max: SalaryBound | None = None
    salary_basis: SalaryBasis | None = None  # local when left out
    comp: Comp | None = None  # base when left out
    # Comma-separated fields, `-` for descending: sort=-hire_date,last_name. Ties are broken
    # by last_name, first_name, id.
    sort: str | None = None
    page: int = Field(default=1, ge=1, le=MAX_PAGE)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class EmployeePage(BaseModel):
    items: list[EmployeeListItem]
    page: int
    page_size: int
    total: int  # every match, not only this page
