"""Money as integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5).

Money is never a float. An amount always travels with its currency.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Final, Self

from salary_api.domain.constants import MAX_AMOUNT_DIGITS, MAX_AMOUNT_MINOR
from salary_api.domain.currency import USD, minor_unit_exponent
from salary_api.domain.rounding import divide_half_even, round_half_even

# An optional sign, ASCII digits, and an optional point followed by more digits.
_PLAIN_DECIMAL = re.compile(r"[+-]?[0-9]+(\.[0-9]+)?")


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
        An amount of 10**15 minor units or more raises InvalidAmountError.

        Works on the digits and exponent, so a hostile input never becomes a huge int.
        """
        sign, digits, exponent = _parse_major(amount).as_tuple()
        if not isinstance(exponent, int):  # NaN or Infinity
            raise InvalidAmountError(f"{amount!r} is not a number")
        if not any(digits):
            return cls(0, currency)
        shift = exponent + minor_unit_exponent(currency)  # amount_minor = digits x 10**shift
        if len(digits) + shift > MAX_AMOUNT_DIGITS:
            raise InvalidAmountError(f"{amount} is too large: the limit is {MAX_AMOUNT_MINOR}")
        if shift < 0 and any(digits[shift:]):
            raise TooManyDecimalsError(f"{amount} has more decimals than {currency} allows")
        kept = digits[:shift] if shift < 0 else digits + (0,) * shift
        amount_minor = int("".join(map(str, kept)))
        return cls(-amount_minor if sign else amount_minor, currency)

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
        return Money(divide_half_even(self.amount_minor, 12), self.currency)

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
    usd_minor = round_half_even(Decimal(money.amount_minor).scaleb(shift) * rate.rate_to_usd)
    return UsdAmount(Money(usd_minor, USD), rate.as_of)


USD_SORT_SCALE: Final = 10**6
"""Sort factors keep six decimals of US cents per local minor unit."""

_INT64_MAX: Final = 2**63 - 1
_HALF: Final = Decimal("0.5")


def min_local_amount(usd_minor: int, rate: FxRate) -> int:
    """The smallest amount (minor units of `rate.currency`, at least 0) worth `usd_minor` or more.

    "Worth" means what `to_usd` gives, half-even rounding included, so a USD salary range
    becomes an exact local range: amount >= min_local_amount(usd_min, rate).
    """
    estimate = (Decimal(usd_minor) - _HALF) / _usd_minor_per_minor(rate)
    amount = max(0, int(estimate.to_integral_value(rounding=ROUND_CEILING)))
    while amount > 0 and _worth(amount - 1, rate) >= usd_minor:
        amount -= 1
    while _worth(amount, rate) < usd_minor:
        amount += 1
    return amount


def max_local_amount(usd_minor: int, rate: FxRate) -> int:
    """The largest amount (minor units of `rate.currency`) worth `usd_minor` or less (see above)."""
    estimate = (Decimal(usd_minor) + _HALF) / _usd_minor_per_minor(rate)
    amount = int(estimate.to_integral_value(rounding=ROUND_FLOOR))
    while _worth(amount + 1, rate) <= usd_minor:
        amount += 1
    while amount > 0 and _worth(amount, rate) > usd_minor:
        amount -= 1
    return amount


@dataclass(frozen=True, slots=True)
class UsdSortKey:
    """`min(amount_minor, cap) * factor` orders amounts of different currencies by USD value.

    `factor` is US cents per local minor unit times USD_SORT_SCALE, rounded half-even: exact
    for rates with up to six decimals (eight for JPY). Amounts above `cap` (over $92 billion at
    a rate of 1) count as `cap`, so the key always fits a signed 64-bit integer. The key only
    orders rows; USD figures shown to users still come from `to_usd`.
    """

    factor: int
    cap: int


def usd_sort_key(rate: FxRate) -> UsdSortKey:
    factor = max(1, round_half_even(_usd_minor_per_minor(rate) * USD_SORT_SCALE))
    return UsdSortKey(factor=factor, cap=_INT64_MAX // factor)


def _usd_minor_per_minor(rate: FxRate) -> Decimal:
    """US cents per minor unit of `rate.currency` (e.g. 0.67 for one yen at 0.0067)."""
    return rate.rate_to_usd.scaleb(minor_unit_exponent(USD) - minor_unit_exponent(rate.currency))


def _worth(amount_minor: int, rate: FxRate) -> int:
    return to_usd(Money(amount_minor, rate.currency), {rate.currency: rate}).amount.amount_minor


def _parse_major(amount: str | Decimal) -> Decimal:
    """The major-unit amount as a Decimal. A float is refused, not converted.

    Text must be a plain ASCII decimal such as `"-52000.50"`: no thousands separators,
    underscores, spaces, exponents or non-ASCII digits (docs/11 §5.2).
    """
    if type(amount) not in (str, Decimal):
        kind = type(amount).__name__
        raise TypeError(f"a major-unit amount must be a str or Decimal, not {kind}")
    if isinstance(amount, Decimal):
        return amount
    if _PLAIN_DECIMAL.fullmatch(amount) is None:
        raise InvalidAmountError(f"{amount!r} is not a number: write it like 52000.50")
    return Decimal(amount)
