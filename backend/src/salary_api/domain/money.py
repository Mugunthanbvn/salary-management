"""Money as integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5).

Money is never a float. An amount always travels with its currency.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Self

from salary_api.domain.currency import USD, minor_unit_exponent


class TooManyDecimalsError(ValueError):
    """The amount has a non-zero digit past the currency's minor unit (e.g. ¥1000.5)."""


class InvalidAmountError(ValueError):
    """The amount is not a finite number (e.g. `"abc"`, `"1,234.56"`, `"NaN"`)."""


class CurrencyMismatchError(ValueError):
    """Two amounts in different currencies were combined. Convert both to USD first."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"Cannot combine {expected} with {actual}")
        self.expected = expected
        self.actual = actual


class InvalidFxRateError(ValueError):
    """The rate is zero, negative or not finite, or a USD rate other than 1."""


class FxRateMissingError(LookupError):
    """No USD rate for a currency. A configuration error: never fall back to 0 or 1."""

    def __init__(self, currency: str) -> None:
        super().__init__(f"No USD rate for {currency}")
        self.currency = currency


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
        numerator, denominator = _parse_major(amount).as_integer_ratio()
        amount_minor, remainder = divmod(
            numerator * 10 ** minor_unit_exponent(currency), denominator
        )
        if remainder:
            raise TooManyDecimalsError(f"{amount} has more decimals than {currency} allows")
        return cls(amount_minor, currency)

    def to_major(self) -> Decimal:
        """The exact amount in major units: 123456 USD cents is `Decimal("1234.56")`."""
        # Built from the digits, so no Decimal context rounding applies at any size.
        sign, digits, _ = Decimal(self.amount_minor).as_tuple()
        return Decimal((sign, digits, -minor_unit_exponent(self.currency)))

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def monthly_display(self) -> "Money":
        """This annual amount ÷ 12, rounded half-even. For display only: never store or sum it."""
        return Money(_divide_half_even(self.amount_minor, 12), self.currency)

    def _require_same_currency(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise CurrencyMismatchError(self.currency, other.currency)


@dataclass(frozen=True, slots=True)
class FxRate:
    """USD per one major unit of `currency` (e.g. INR `Decimal("0.01198")`), valid as of a date."""

    currency: str
    rate_to_usd: Decimal
    as_of: date

    def __post_init__(self) -> None:
        if type(self.rate_to_usd) is not Decimal:
            kind = type(self.rate_to_usd).__name__
            raise TypeError(f"rate_to_usd must be a Decimal, not {kind}")
        minor_unit_exponent(self.currency)  # raises UnknownCurrencyError
        if not self.rate_to_usd.is_finite() or self.rate_to_usd <= 0:
            raise InvalidFxRateError(f"{self.currency} rate must be positive: {self.rate_to_usd}")
        if self.currency == USD and self.rate_to_usd != 1:
            raise InvalidFxRateError(f"{USD} rate must be 1, not {self.rate_to_usd}")


@dataclass(frozen=True, slots=True)
class UsdAmount:
    """An amount converted to USD, with the `as_of` date of the rate used."""

    amount: Money
    fx_as_of: date


def to_usd(money: Money, rates: Mapping[str, FxRate]) -> UsdAmount:
    """Convert to USD at read time (docs/09 §2.6). The source Money is never changed.

    usd_minor = round_half_even(amount_minor * 10**(2 - exp) * rate_to_usd), all in Decimal.
    """
    rate = rates.get(money.currency)
    if rate is None:
        raise FxRateMissingError(money.currency)
    if rate.currency != money.currency:
        raise CurrencyMismatchError(money.currency, rate.currency)
    shift = minor_unit_exponent(USD) - minor_unit_exponent(money.currency)
    usd_minor = _round_half_even(Decimal(money.amount_minor).scaleb(shift) * rate.rate_to_usd)
    return UsdAmount(Money(usd_minor, USD), rate.as_of)


def _round_half_even(value: Decimal) -> int:
    """`value` rounded to the nearest int, ties to even (2.5 -> 2, 3.5 -> 4)."""
    return int(value.to_integral_value(rounding=ROUND_HALF_EVEN))


def _divide_half_even(numerator: int, denominator: int) -> int:
    """`numerator / denominator` rounded to the nearest int, ties to even, in exact int maths."""
    quotient, remainder = divmod(numerator, denominator)
    twice_remainder = 2 * remainder
    if twice_remainder > denominator or (twice_remainder == denominator and quotient % 2 == 1):
        quotient += 1
    return quotient


def _parse_major(amount: str | Decimal) -> Decimal:
    """The major-unit amount as a finite Decimal. A float is refused, not converted."""
    if type(amount) not in (str, Decimal):
        kind = type(amount).__name__
        raise TypeError(f"a major-unit amount must be a str or Decimal, not {kind}")
    try:
        value = Decimal(amount)
    except InvalidOperation:
        raise InvalidAmountError(f"{amount!r} is not a number") from None
    if not value.is_finite():
        raise InvalidAmountError(f"{amount!r} is not a number")
    return value
