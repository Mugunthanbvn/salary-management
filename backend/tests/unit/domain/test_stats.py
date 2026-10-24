"""Statistics over integer minor amounts (docs/09-insights-pay-equity.md §2.7, ADR 0007)."""

import statistics
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.stats import InsufficientData, Summary, summarize

# Seven EUR salaries in cents; NumPy percentile(..., [25, 50, 75]) = 5000000, 5400000, 6650000.
SALARIES = [4200000, 4900000, 5100000, 5400000, 6300000, 7000000, 14500000]

amount_lists = st.lists(st.integers(min_value=0, max_value=10**12), min_size=1, max_size=50)


def summary_of(amounts: list[int]) -> Summary:
    result = summarize(amounts)
    assert isinstance(result, Summary)
    return result


def test_an_empty_input_is_insufficient_data_not_zero_or_an_error() -> None:
    result = summarize([])

    assert result == InsufficientData()


def test_a_single_value_is_every_statistic() -> None:
    result = summarize([5200000])

    assert result == Summary(
        count=1,
        min=5200000,
        p25=5200000,
        median=5200000,
        mean=5200000,
        p75=5200000,
        max=5200000,
        sum=5200000,
    )


def test_count_min_max_and_sum_describe_the_whole_group() -> None:
    result = summary_of([500, 100, 300])

    assert (result.count, result.min, result.max, result.sum) == (3, 100, 500, 900)


def test_median_of_odd_count_is_the_middle_value() -> None:
    result = summary_of([300, 100, 200])

    assert result.median == 200


def test_median_of_even_count_is_mean_of_middle_two() -> None:
    result = summary_of([400, 100, 300, 200])

    assert result.median == 250


@pytest.mark.parametrize(
    ("amounts", "p25", "median", "p75"),
    [
        ([1, 2, 3, 4, 5], 2, 3, 4),
        ([10, 20, 30, 40], 18, 25, 32),  # exact 17.5, 25, 32.5: ties go to the even neighbour
        ([1, 4, 9, 16, 25, 36], 5, 12, 23),  # exact 5.25, 12.5, 22.75
        (SALARIES, 5000000, 5400000, 6650000),
    ],
)
def test_quartiles_interpolate_linearly_between_closest_ranks(
    amounts: list[int], p25: int, median: int, p75: int
) -> None:
    result = summary_of(amounts)

    assert (result.p25, result.median, result.p75) == (p25, median, p75)


@pytest.mark.parametrize(
    ("amounts", "mean"),
    [([1, 2], 2), ([0, 1], 0), ([3, 4], 4), ([1, 2, 2], 2), ([1, 2, 4], 2), (SALARIES, 6771429)],
)
def test_mean_is_sum_over_count_rounded_half_even(amounts: list[int], mean: int) -> None:
    result = summary_of(amounts)

    assert result.mean == mean


@given(amount_lists)
def test_stats_are_ordered_from_min_to_max(amounts: list[int]) -> None:
    result = summary_of(amounts)

    assert result.min <= result.p25 <= result.median <= result.p75 <= result.max
    assert result.min <= result.mean <= result.max


@given(amount_lists.flatmap(lambda amounts: st.tuples(st.just(amounts), st.permutations(amounts))))
def test_stats_do_not_depend_on_input_order(lists: tuple[list[int], list[int]]) -> None:
    amounts, shuffled = lists

    assert summarize(shuffled) == summarize(amounts)


@given(amount_lists)
def test_quartiles_match_the_inclusive_method_of_statistics_quantiles(amounts: list[int]) -> None:
    exact = statistics.quantiles([Fraction(a) for a in amounts], n=4, method="inclusive")

    result = summary_of(amounts)

    # round() on a Fraction is exact and half-even, like NumPy linear + our rounding.
    assert (result.p25, result.median, result.p75) == tuple(round(q) for q in exact)
