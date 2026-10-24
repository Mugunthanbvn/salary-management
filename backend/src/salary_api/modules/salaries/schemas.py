from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from salary_api.core.schemas import Money
from salary_api.domain.constants import MAX_AMOUNT_MINOR
from salary_api.domain.enums import ComponentType

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
