"""Insight queries and responses (docs/07-api-spec.md section 8, docs/glossary.md section 6)."""

from pydantic import BaseModel, ConfigDict, Field

from salary_api.core.schemas import Comp, Id
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.modules.reference.schemas import CountryCode


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


class Population(BaseModel):
    """The filters actually applied. An empty list means no condition on that field."""

    country: list[str]
    department_id: list[int]
    job_role_id: list[int]
    level: list[Level]
    employment_type: list[EmploymentType]
    status: list[EmployeeStatus]
    comp: Comp


class Overview(BaseModel):
    population: Population
    headcount: int
