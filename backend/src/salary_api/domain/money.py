"""Money as integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5).

Money is never a float. An amount always travels with its currency.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from salary_api.domain.currency import minor_unit_exponent


@dataclass(frozen=True, slots=True)
class Money:
    """An exact amount: `amount_minor` counts the currency's minor unit (cents, paise, yen)."""

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        # Checked at run time as well: a float (or bool) must never become money.
        if type(self.amount_minor) is not int:
            kind = type(self.amount_minor).__name__
            raise TypeError(f"amount_minor must be an int of minor units, not {kind}")
        minor_unit_exponent(self.currency)  # raises UnknownCurrencyError

    @classmethod
    def from_major(cls, amount: str | Decimal, currency: str) -> Self:
        """Money from a major-unit amount: `from_major("1234.56", "USD")` is 123456 cents."""
        numerator, denominator = Decimal(amount).as_integer_ratio()
        return cls(numerator * 10 ** minor_unit_exponent(currency) // denominator, currency)
