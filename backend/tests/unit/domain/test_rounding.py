"""Half-even rounding, checked against Python's exact Fraction rounding (also half-even)."""

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.rounding import divide_half_even, round_half_even


@pytest.mark.parametrize(
    ("value", "rounded"),
    [("0.5", 0), ("1.5", 2), ("2.5", 2), ("-0.5", 0), ("-1.5", -2), ("2.4999", 2), ("2.5001", 3)],
)
def test_round_half_even_sends_ties_to_the_even_neighbour(value: str, rounded: int) -> None:
    assert round_half_even(Decimal(value)) == rounded


@given(numerator=st.integers(), denominator=st.integers(min_value=1))
def test_divide_half_even_matches_exact_fraction_rounding(numerator: int, denominator: int) -> None:
    assert divide_half_even(numerator, denominator) == round(Fraction(numerator, denominator))
