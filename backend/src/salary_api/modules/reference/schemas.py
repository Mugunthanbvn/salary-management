from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from salary_api.core.schemas import Id
from salary_api.domain.enums import EmploymentType, Level, SalaryReason
from salary_api.modules.reference.models import JobFamily

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]  # ISO 3166-1 alpha-2
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]  # ISO 4217


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


class PayBandQuery(BaseModel):
    """Filters of GET /pay-bands; repeat a key for several values."""

    model_config = ConfigDict(extra="forbid")

    country: list[CountryCode] = Field(default_factory=list[CountryCode])
    job_role_id: list[Id] = Field(default_factory=list[Id])
    level: list[Level] = Field(default_factory=list[Level])


class PayBandItem(BaseModel):
    """The band in force for a job role + level + country, in minor units of `currency`."""

    job_role_id: int
    level: Level
    country_code: str
    currency: str
    min: int
    mid: int
    max: int
    effective_from: date


class PayBands(BaseModel):
    bands: list[PayBandItem]  # by country, job role id, level


class FxRateItem(BaseModel):
    currency: str
    rate_to_usd: str  # USD per one major unit, as a decimal string (no float rounding)
    as_of: date
    source: str


class FxRates(BaseModel):
    rates: list[FxRateItem]  # by currency
