from pydantic import BaseModel

from salary_api.domain.enums import EmploymentType, Level, SalaryReason
from salary_api.modules.reference.models import JobFamily


class Country(BaseModel):
    code: str
    name: str
    default_currency: str
    is_active: bool


class Department(BaseModel):
    id: int
    name: str


class JobRole(BaseModel):
    id: int
    title: str
    department_id: int
    family: JobFamily


class JobRoleRef(BaseModel):
    """A job role as other resources show it."""

    id: int
    title: str


class LevelOption(BaseModel):
    code: Level
    label: str


class CurrencyOption(BaseModel):
    code: str
    exponent: int  # decimal places of the minor unit: JPY 0, the others 2


class ReferenceData(BaseModel):
    """Every dropdown value, and what filters are validated against (docs/07 section 5)."""

    countries: list[Country]
    departments: list[Department]
    job_roles: list[JobRole]
    levels: list[LevelOption]
    employment_types: list[EmploymentType]
    currencies: list[CurrencyOption]
    salary_change_reasons: list[SalaryReason]
