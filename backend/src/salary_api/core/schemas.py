"""API shapes and parameters shared by several modules (docs/glossary.md section 6)."""

from enum import StrEnum
from typing import Annotated, Final

from pydantic import BaseModel, Field

# docs/glossary.md section 3: page size default 25, max 100.
DEFAULT_PAGE_SIZE: Final = 25
MAX_PAGE_SIZE: Final = 100

MAX_ID: Final = 2**63 - 1
"""The largest value of a 64-bit integer column; a larger id would overflow SQLite."""
MAX_PAGE: Final = MAX_ID // MAX_PAGE_SIZE
"""So that the offset (page - 1) * page_size always fits a 64-bit integer."""

Id = Annotated[int, Field(ge=1, le=MAX_ID)]
"""A row id in a query or body: 1 to MAX_ID, else 422."""


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


class FileFormat(StrEnum):
    """The file a download is written as: `?format=csv|xlsx`."""

    CSV = "csv"
    XLSX = "xlsx"
