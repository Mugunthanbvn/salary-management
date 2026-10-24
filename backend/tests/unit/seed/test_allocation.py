"""Largest-remainder allocation: exact counts for any total (docs/12-seed-data.md section 2)."""

from hypothesis import given
from hypothesis import strategies as st

from salary_api.seed.allocation import largest_remainder


def test_ten_thousand_employees_split_exactly_by_country_share() -> None:
    shares = [30, 25, 10, 8, 6, 5, 5, 4, 4, 3]

    assert largest_remainder(10_000, shares) == [
        3000,
        2500,
        1000,
        800,
        600,
        500,
        500,
        400,
        400,
        300,
    ]


def test_the_largest_remainders_get_the_leftover_units() -> None:
    assert largest_remainder(7, [50, 30, 20]) == [4, 2, 1]  # quotas 3.5, 2.1, 1.4


def test_equal_remainders_go_to_the_earlier_item() -> None:
    assert largest_remainder(5, [1, 1, 1]) == [2, 2, 1]


def test_nothing_to_split_gives_zeros() -> None:
    assert largest_remainder(0, [30, 70]) == [0, 0]


@given(
    total=st.integers(min_value=0, max_value=50_000),
    weights=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=12).filter(
        lambda weights: sum(weights) > 0
    ),
)
def test_parts_add_up_to_the_total_and_stay_within_one_of_their_quota(
    total: int, weights: list[int]
) -> None:
    parts = largest_remainder(total, weights)

    assert sum(parts) == total
    for part, weight in zip(parts, weights, strict=True):
        assert total * weight // sum(weights) <= part <= total * weight // sum(weights) + 1
