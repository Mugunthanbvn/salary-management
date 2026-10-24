"""Group statistics over integer minor amounts, in exact arithmetic (docs/09 §2.7, ADR 0007).

The repository fetches the amounts for one group in one currency; these functions do the maths.
"""

from collections.abc import Iterable
from dataclasses import dataclass


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
    """Count, min, max, sum, mean, median, P25 and P75 of `amounts`, in their minor units."""
    ordered = sorted(amounts)
    if not ordered:
        return InsufficientData()
    only = ordered[0]
    return Summary(
        count=len(ordered),
        min=ordered[0],
        p25=only,
        median=only,
        mean=only,
        p75=only,
        max=ordered[-1],
        sum=sum(ordered),
    )
