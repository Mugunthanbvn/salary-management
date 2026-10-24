from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from salary_api.core.schemas import Money
from salary_api.domain.constants import MAX_AMOUNT_MINOR
from salary_api.domain.enums import ComponentType, Level, SalaryReason
from salary_api.modules.reference.schemas import CountryCode, CurrencyCode, JobRoleRef

# Amounts arrive as JSON integers of minor units: strict, so 5400000.0 and "5400000" are refused
# rather than converted (docs/06-data-model.md section 5.1).
AmountMinor = Annotated[int, Field(strict=True, ge=0, le=MAX_AMOUNT_MINOR)]
BaseMinor = Annotated[int, Field(strict=True, gt=0, le=MAX_AMOUNT_MINOR)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
# Packages have a handful of components; the cap keeps one request small.
MAX_COMPONENTS = 20


class ComponentIn(BaseModel):
    """An annual allowance or bonus target, in the salary's currency."""

    model_config = ConfigDict(extra="forbid")

    type: ComponentType
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    amount_minor: AmountMinor


def _each_type_and_name_once(components: list[ComponentIn]) -> list[ComponentIn]:
    keys = [(component.type, component.name) for component in components]
    if len(keys) != len(set(keys)):
        raise ValueError("Each component type and name may appear only once.")
    return components


Components = Annotated[
    list[ComponentIn], Field(max_length=MAX_COMPONENTS), AfterValidator(_each_type_and_name_once)
]


class Component(BaseModel):
    type: ComponentType
    name: str
    amount: Money


class SalaryChangeRequest(BaseModel):
    """A new salary record. Role, level and country default to the current ones."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)  # the employee version the client read
    effective_date: date
    reason: SalaryReason
    job_role_id: int | None = None  # a new role; PROMOTION needs a new role or a higher level
    level: Level | None = None
    country_code: CountryCode | None = None  # a relocation; the salary currency follows it
    currency: CurrencyCode | None = None  # must be the (new) country's currency
    base_minor: BaseMinor
    # Replaces the component set; nothing is inherited from the current record.
    components: Components = []
    note: Note | None = None


class ChangedBy(BaseModel):
    id: int
    full_name: str


class SalaryHistoryRecord(BaseModel):
    id: int
    effective_date: date
    reason: SalaryReason
    job_role: JobRoleRef  # the role and level at that time
    level: Level
    base: Money
    total: Money
    components: list[Component]
    # Percent change of base from the previous record, e.g. "12.50"; null for the first
    # record and when the currency changed.
    base_change_pct: str | None
    changed_by: ChangedBy | None  # null for seeded history
    note: str | None
    created_at: datetime


class SalaryChange(BaseModel):
    record: SalaryHistoryRecord
    employee_version: int  # send it with the employee's next change
