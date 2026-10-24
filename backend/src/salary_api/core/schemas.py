"""Response shapes shared by several modules (docs/glossary.md section 6)."""

from typing import Final

from pydantic import BaseModel

# docs/glossary.md section 3: page size default 25, max 100.
DEFAULT_PAGE_SIZE: Final = 25
MAX_PAGE_SIZE: Final = 100


class Money(BaseModel):
    """An exact amount: integer minor units of an ISO 4217 currency, never a float."""

    amount_minor: int
    currency: str
