"""Hypothesis strategies for domain values (supported currencies, Money, major amounts)."""

from decimal import Decimal

from hypothesis import strategies as st

from salary_api.domain.currency import SUPPORTED_CURRENCIES, minor_unit_exponent

# The largest amount from_major accepts: fewer than 10**15 minor units (docs/06 §5.1).
LARGEST_AMOUNT_MINOR = 10**15 - 1

currencies = st.sampled_from(sorted(SUPPORTED_CURRENCIES))
amounts_minor = st.integers(min_value=-LARGEST_AMOUNT_MINOR, max_value=LARGEST_AMOUNT_MINOR)


@st.composite
def major_amounts(draw: st.DrawFn) -> tuple[Decimal, str]:
    """A currency and a major-unit amount that from_major accepts for it."""
    currency = draw(currencies)
    places = minor_unit_exponent(currency)
    largest = Decimal(LARGEST_AMOUNT_MINOR).scaleb(-places)
    amount = draw(st.decimals(min_value=-largest, max_value=largest, places=places))
    return amount, currency
