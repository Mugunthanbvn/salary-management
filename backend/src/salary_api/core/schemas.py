"""API shapes and parameters shared by several modules (docs/glossary.md section 6)."""

from enum import StrEnum
from typing import Final

from pydantic import BaseModel

# docs/glossary.md section 3: page size default 25, max 100.
DEFAULT_PAGE_SIZE: Final = 25
MAX_PAGE_SIZE: Final = 100


class Money(BaseModel):
    """An exact amount: integer minor units of an ISO 4217 currency, never a float."""

    amount_minor: int
    currency: str


class SalaryBasis(StrEnum):
    """How salaries in different currencies are compared: in local currency, or in USD."""

    LOCAL = "local"
    USD = "usd"


class Comp(StrEnum):
    """Which amount a salary filter or statistic uses: the base or the total compensation."""

    BASE = "base"
    TOTAL = "total"
