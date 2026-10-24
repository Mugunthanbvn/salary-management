"""Hypothesis strategies for domain values (supported currencies, Money, major amounts)."""

from decimal import Decimal

from hypothesis import strategies as st

from salary_api.domain.currency import SUPPORTED_CURRENCIES, minor_unit_exponent

currencies = st.sampled_from(sorted(SUPPORTED_CURRENCIES))


@st.composite
def major_amounts(draw: st.DrawFn) -> tuple[Decimal, str]:
    """A currency and a finite major-unit amount with no more decimals than it allows."""
    currency = draw(currencies)
    places = minor_unit_exponent(currency)
    amount = draw(st.decimals(allow_nan=False, allow_infinity=False, places=places))
    return amount, currency
