"""Response shapes shared by several modules (docs/glossary.md section 6)."""

from pydantic import BaseModel


class Money(BaseModel):
    """An exact amount: integer minor units of an ISO 4217 currency, never a float."""

    amount_minor: int
    currency: str
