"""Money as integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5).

Money is never a float. An amount always travels with its currency.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from salary_api.domain.currency import minor_unit_exponent


class TooManyDecimalsError(ValueError):
    """The amount has a non-zero digit past the currency's minor unit (e.g. ¥1000.5)."""


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
        """Money from a major-unit amount: `from_major("1234.56", "USD")` is 123456 cents.

        Too many decimals are rejected, never rounded: `"1000.5"` JPY raises
        TooManyDecimalsError. Trailing zeros lose nothing, so `"1000.0"` JPY is ¥1000.
        """
        numerator, denominator = Decimal(amount).as_integer_ratio()
        amount_minor, remainder = divmod(
            numerator * 10 ** minor_unit_exponent(currency), denominator
        )
        if remainder:
            raise TooManyDecimalsError(f"{amount} has more decimals than {currency} allows")
        return cls(amount_minor, currency)
