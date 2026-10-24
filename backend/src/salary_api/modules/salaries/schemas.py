from pydantic import BaseModel, ConfigDict

from salary_api.core.schemas import Money
from salary_api.domain.enums import ComponentType


class ComponentIn(BaseModel):
    """An annual allowance or bonus target, in the salary's currency."""

    model_config = ConfigDict(extra="forbid")

    type: ComponentType
    name: str
    amount_minor: int


class Component(BaseModel):
    type: ComponentType
    name: str
    amount: Money
