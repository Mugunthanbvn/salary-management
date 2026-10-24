"""ISO 4217 minor-unit exponents for the currencies ACME pays in.

The exponent is the number of decimal places of the currency's minor unit:
USD has cents (2), JPY has no minor unit (0). See docs/06-data-model.md §5.1.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

_MINOR_UNIT_EXPONENTS: Final[Mapping[str, int]] = MappingProxyType(
    {
        "USD": 2,
        "INR": 2,
        "GBP": 2,
        "EUR": 2,
        "CAD": 2,
        "SGD": 2,
        "AUD": 2,
        "JPY": 0,
        "BRL": 2,
    }
)

SUPPORTED_CURRENCIES: Final = frozenset(_MINOR_UNIT_EXPONENTS)

USD: Final = "USD"
"""The reporting currency: cross-currency figures are converted to it (ADR 0005)."""


class UnknownCurrencyError(ValueError):
    """The code is not one of the supported ISO 4217 currencies (codes are upper case)."""


def minor_unit_exponent(currency: str) -> int:
    """The number of decimal places in one major unit of `currency` (USD 2, JPY 0)."""
    try:
        return _MINOR_UNIT_EXPONENTS[currency]
    except KeyError:
        raise UnknownCurrencyError(f"Unsupported currency: {currency!r}") from None
