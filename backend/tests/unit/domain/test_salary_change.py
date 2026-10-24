"""Rules for salary changes (docs/07-api-spec.md 6.6-6.7, docs/06-data-model.md 6.1)."""


import pytest

from salary_api.domain.enums import Level
from salary_api.domain.money import Money
from salary_api.domain.salary_change import base_change_pct, is_promotion


@pytest.mark.parametrize(
    ("old_level", "new_level", "new_role_id", "promotion"),
    [
        pytest.param(Level.L2, Level.L3, 7, True, id="higher level"),
        pytest.param(Level.L3, Level.L3, 8, True, id="different role"),
        pytest.param(Level.L4, Level.L3, 8, True, id="different role, lower level"),
        pytest.param(Level.L3, Level.L3, 7, False, id="same level and role"),
        pytest.param(Level.L4, Level.L3, 7, False, id="lower level"),
        pytest.param(Level.L5, Level.L6, 7, True, id="to director"),
    ],
)
def test_a_promotion_is_a_higher_level_or_a_different_role(
    old_level: Level, new_level: Level, new_role_id: int, promotion: bool
) -> None:
    result = is_promotion(
        old_level=old_level, new_level=new_level, old_role_id=7, new_role_id=new_role_id
    )

    assert result is promotion


@pytest.mark.parametrize(
    ("previous", "current", "pct"),
    [
        pytest.param(180_000_000, 216_000_000, "20.00", id="raise"),
        pytest.param(8_000_000, 9_000_000, "12.50", id="keeps two decimals"),
        pytest.param(1_000_000, 900_000, "-10.00", id="cut"),
        pytest.param(6_000_000, 6_000_000, "0.00", id="unchanged"),
        pytest.param(800, 801, "0.12", id="0.125 rounds half-even down"),
        pytest.param(800, 803, "0.38", id="0.375 rounds half-even up"),
        pytest.param(3, 4, "33.33", id="repeating decimal"),
    ],
)
def test_base_change_pct_is_the_percent_change_rounded_half_even(
    previous: int, current: int, pct: str
) -> None:
    change = base_change_pct(Money(previous, "INR"), Money(current, "INR"))

    assert change is not None
    assert str(change) == pct


def test_base_change_pct_is_none_when_the_currency_changed() -> None:
    assert base_change_pct(Money(6_000_000, "EUR"), Money(9_000_000, "USD")) is None
