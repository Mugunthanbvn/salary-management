"""Insight queries and responses (docs/07-api-spec.md section 8, docs/glossary.md section 6)."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from salary_api.core.schemas import Comp, Id, Money
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level, PayEquityFlag
from salary_api.domain.pay_equity import NoCompaRatioReason
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


MAX_TOP_EARNERS: Final = 50


class Direction(StrEnum):
    TOP = "top"  # the highest paid first
    BOTTOM = "bottom"  # the lowest paid first


class TopEarnersQuery(InsightFilters):
    """The query of top-earners: one country, so everyone is ranked in one currency."""

    country: CountryCode
    comp: Comp = Comp.BASE
    n: int = Field(default=10, ge=1, le=MAX_TOP_EARNERS)
    direction: Direction = Direction.TOP


class PayEquityView(StrEnum):
    COHORTS = "cohorts"  # per job role + level + country
    DEPARTMENTS = "departments"  # per department in one country: the systemic-gap view


class PayEquityQuery(InsightFilters):
    """The query of pay-equity. There is no `comp`: bands are defined on base pay."""

    view: PayEquityView = PayEquityView.COHORTS
    country: list[CountryCode] = Field(default_factory=list[CountryCode])


class CohortQuery(BaseModel):
    """The query of pay-equity/cohort: one job role, level and country."""

    model_config = ConfigDict(extra="forbid")

    job_role_id: Id
    level: Level
    country: CountryCode
    employment_type: list[EmploymentType] = Field(
        default_factory=lambda: [EmploymentType.FULL_TIME]
    )
    status: list[EmployeeStatus] = Field(default_factory=lambda: [EmployeeStatus.ACTIVE])


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


class DepartmentCost(BaseModel):
    """One department's pay bill: the sum of its people's amounts (docs/09 section 3.5)."""

    department: Department
    headcount: int | None
    cost: Money | None  # in the response currency
    cost_usd: Money | None  # each amount converted to USD, then summed
    share_of_total: str | None  # cost / total, 4 decimals; null when either is hidden
    suppressed: bool


class DepartmentCosts(BaseModel):
    """In local currency (with USD next to it) for one currency's countries, else in USD."""

    population: Population
    currency: str
    fx_as_of: date | None
    headcount: int | None
    total: Money | None
    total_usd: Money | None
    suppressed: bool  # the whole population is under MIN_GROUP_SIZE for this caller
    groups: list[DepartmentCost]  # by department name


class Earner(BaseModel):
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    job_role: JobRoleRef
    level: Level
    department: Department
    amount: Money  # base or total, as asked, in the country's currency


class TopEarners(BaseModel):
    """docs/09 section 3.6: individuals, so SALARY_READ only. Ties go by employee code."""

    population: Population
    country_code: str
    currency: str
    direction: Direction
    n: int
    items: list[Earner]


class Thresholds(BaseModel):
    """Compa-ratio limits as decimal strings: below `low` is UNDERPAID, above `high` is
    OVERPAID, and a department whose median is below `rollup` is below threshold."""

    low: str
    high: str
    rollup: str


class Band(BaseModel):
    """A pay band in minor units of `currency`. Policy, not anyone's pay: never hidden."""

    min: int
    mid: int
    max: int
    currency: str


class PayEquitySummary(BaseModel):
    """Who was evaluated, who was left out and why, and who was flagged.

    For a caller without SALARY_READ, all counts are null when fewer than 5 were evaluated.
    """

    employees_evaluated: int | None
    employees_without_band: int | None
    employees_not_full_time: int | None  # part-time pay is not FTE-normalised
    employees_flagged_underpaid: int | None
    employees_flagged_overpaid: int | None
    suppressed: bool


class CohortEquity(BaseModel):
    """One job role + level + country against its band. Ratios are 2-decimal strings."""

    job_role: JobRoleRef
    level: Level
    country_code: str
    department: Department
    stats: Stats  # base pay of the members with a compa-ratio, in local currency
    band: Band
    median_compa_ratio: str | None
    underpaid_count: int | None
    overpaid_count: int | None
    suppressed: bool


class PayEquityCohorts(BaseModel):
    view: Literal[PayEquityView.COHORTS]
    population: Population
    thresholds: Thresholds
    cohorts: list[CohortEquity]  # by job role id, level, country
    summary: PayEquitySummary


class DepartmentEquity(BaseModel):
    """One department in one country: is the team as a whole paid below its bands?"""

    department: Department
    count: int | None  # employees with a compa-ratio
    median_compa_ratio: str | None
    mean_compa_ratio: str | None
    pct_below_band: str | None  # the share flagged UNDERPAID, from 0 to 1
    underpaid_count: int | None
    overpaid_count: int | None
    below_threshold: bool | None  # median compa-ratio below `thresholds.rollup`
    suppressed: bool


class PayEquityDepartments(BaseModel):
    view: Literal[PayEquityView.DEPARTMENTS]
    population: Population
    country_code: str
    thresholds: Thresholds
    groups: list[DepartmentEquity]  # by department name
    summary: PayEquitySummary


PayEquity = Annotated[PayEquityCohorts | PayEquityDepartments, Field(discriminator="view")]


class CohortMember(BaseModel):
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    employment_type: EmploymentType
    base: Money
    compa_ratio: str | None  # base / band midpoint, 2 decimals
    flag: PayEquityFlag | None  # decided on the unrounded ratio
    no_compa_ratio_reason: NoCompaRatioReason | None  # why compa_ratio is null


class CohortMembers(BaseModel):
    """One cohort's people against its band (docs/07 8.11). SALARY_READ only; audited."""

    population: Population
    job_role: JobRoleRef
    level: Level
    country_code: str
    department: Department
    currency: str
    band: Band | None  # None when the cohort has no band
    thresholds: Thresholds
    members: list[CohortMember]  # lowest compa-ratio first, then those without one
