from datetime import date

from pydantic import BaseModel, ConfigDict

from salary_api.core.schemas import Money
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level, SalaryReason
from salary_api.modules.reference.schemas import Department, JobRoleRef
from salary_api.modules.salaries.schemas import Component, ComponentIn


class HireSalary(BaseModel):
    """The first salary. `currency` may be left out: it is always the country's currency."""

    model_config = ConfigDict(extra="forbid")

    currency: str | None = None
    base_minor: int
    components: list[ComponentIn] = []
    note: str | None = None


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_code: str | None = None
    first_name: str
    last_name: str
    email: str
    job_role_id: int
    level: Level
    employment_type: EmploymentType
    country_code: str
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
