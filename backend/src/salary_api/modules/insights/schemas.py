"""Insight queries and responses (docs/07-api-spec.md section 8, docs/glossary.md section 6)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from salary_api.core.schemas import Comp, Id, Money
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.modules.reference.schemas import CountryCode, Department, JobRoleRef


class InsightFilters(BaseModel):
    """Who an insight covers: full-time, active employees unless the caller says otherwise.

    Repeat a key for several values (`?level=L2&level=L3`): values of one key are ORed,
    different keys are ANDed. Unknown parameters are refused (422), so typos show.
    """

    model_config = ConfigDict(extra="forbid")

    department_id: list[Id] = Field(default_factory=list[Id])
    job_role_id: list[Id] = Field(default_factory=list[Id])
    level: list[Level] = Field(default_factory=list[Level])
    # Part-time pay is not full-time-equivalent, so it is left out unless asked for.
    employment_type: list[EmploymentType] = Field(
        default_factory=lambda: [EmploymentType.FULL_TIME]
    )
    status: list[EmployeeStatus] = Field(default_factory=lambda: [EmployeeStatus.ACTIVE])


class InsightQuery(InsightFilters):
    """The query of overview, by-department and department-cost (docs/07 section 8.1)."""

    country: list[CountryCode] = Field(default_factory=list[CountryCode])
    comp: Comp = Comp.BASE  # base, or total = base + allowances + bonus target


class JobTitleQuery(InsightFilters):
    """The query of by-job-title: one country, since titles compare within one market."""

    country: CountryCode
    comp: Comp = Comp.BASE
    split_by_level: bool = False


class Population(BaseModel):
    """The filters actually applied. An empty list means no condition on that field."""

    country: list[str]
    department_id: list[int]
    job_role_id: list[int]
    level: list[Level]
    employment_type: list[EmploymentType]
    status: list[EmployeeStatus]
    comp: Comp


class Stats(BaseModel):
    """One group's statistics in minor units of `currency` (docs/07 section 8.2).

    Percentiles interpolate linearly; mean and percentiles are rounded half-even.
    """

    count: int | None
    min: int | None
    p25: int | None
    median: int | None
    mean: int | None
    p75: int | None
    max: int | None
    currency: str
    suppressed: bool


class CountryStats(BaseModel):
    """One country: in its own currency, and with each salary converted to USD."""

    country_code: str
    local: Stats
    usd: Stats


class Overview(BaseModel):
    """docs/09 section 3.1. `stats` is in `currency`: the population's one currency, else USD."""

    population: Population
    currency: str
    fx_as_of: date | None  # the oldest rate used for a USD figure; None when none was needed
    headcount: int | None  # null when the population is suppressed
    total_payroll_usd: Money | None
    stats: Stats
    by_country: list[CountryStats]


class DepartmentStats(BaseModel):
    department: Department
    stats: Stats


class ByDepartment(BaseModel):
    """docs/09 section 3.2: in local currency for one currency's countries, else in USD."""

    population: Population
    currency: str
    fx_as_of: date | None
    groups: list[DepartmentStats]  # by department name


class JobTitleStats(BaseModel):
    job_role: JobRoleRef
    level: Level | None  # only with split_by_level
    stats: Stats


class ByJobTitle(BaseModel):
    """docs/09 section 3.3: always in the country's currency."""

    population: Population
    currency: str
    split_by_level: bool
    groups: list[JobTitleStats]  # by title, then level
