"""Group statistics over integer minor amounts, in exact arithmetic (docs/09 §2.7, ADR 0007).

The repository fetches the amounts for one group in one currency; these functions do the maths.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from salary_api.domain.rounding import divide_half_even, round_half_even

P25 = Decimal("0.25")
P50 = Decimal("0.5")
P75 = Decimal("0.75")


@dataclass(frozen=True, slots=True)
class InsufficientData:
    """There are no amounts to summarise. Show an empty state, never zeros."""


@dataclass(frozen=True, slots=True)
class Summary:
    """The stats object of docs/07 §8.2, all in the group's minor units."""

    count: int
    min: int
    p25: int
    median: int
    mean: int
    p75: int
    max: int
    sum: int


def summarize(amounts: Iterable[int]) -> Summary | InsufficientData:
    """Count, min, max, sum, mean, median, P25 and P75 of `amounts`, in their minor units.

    Mean and percentiles are rounded half-even to the minor unit. The order of `amounts`
    does not matter.
    """
    ordered = sorted(amounts)
    if not ordered:
        return InsufficientData()
    total = sum(ordered)
    return Summary(
        count=len(ordered),
        min=ordered[0],
        p25=round_half_even(_percentile(ordered, P25)),
        median=round_half_even(_percentile(ordered, P50)),
        mean=divide_half_even(total, len(ordered)),
        p75=round_half_even(_percentile(ordered, P75)),
        max=ordered[-1],
        sum=total,
    )


def median(values: Iterable[Decimal]) -> Decimal:
    """The exact, unrounded median of `values`, such as compa-ratios. Needs at least one value."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median of no values")
    return _percentile(ordered, P50)


def _percentile[N: (int, Decimal)](ordered: Sequence[N], p: Decimal) -> Decimal:
    """Linear interpolation between closest ranks (NumPy "linear", SQL PERCENTILE_CONT).

    `ordered` is sorted and not empty. The result is exact, not rounded.
    """
    h = (len(ordered) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return ordered[lo] + (h - lo) * (ordered[hi] - ordered[lo])
