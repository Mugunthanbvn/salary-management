"""The seed's pay formula, pay bands and components (docs/12-seed-data.md sections 5, 6 and 8)."""

import random
import statistics
from decimal import Decimal

import pytest

from salary_api.domain.enums import ComponentType, EmploymentType, Level, PayEquityFlag
from salary_api.domain.pay_equity import flag
from salary_api.seed import seed_config as config
from salary_api.seed.pay import (
    Band,
    ComponentAmount,
    band_for,
    components_for,
    draw_noise,
    draw_uniform,
    reference_minor,
    round_to_unit,
    rounding_unit_minor,
)
from salary_api.seed.seed_config import CountrySpec

BOUNDS = (Decimal("0.89"), Decimal("1.12"))
COUNTRY = {country.code: country for country in config.COUNTRIES}
ROLE = {role.title: role for department in config.DEPARTMENTS for role in department.roles}
FULL_TIME, PART_TIME, CONTRACTOR = (
    EmploymentType.FULL_TIME,
    EmploymentType.PART_TIME,
    EmploymentType.CONTRACTOR,
)


def test_the_worked_example_india_software_engineer_l2_has_a_band_mid_of_22_20_000_rupees() -> None:
    reference = reference_minor(Level.L2, ROLE["Software Engineer"], COUNTRY["IN"])
    band = band_for(Level.L2, ROLE["Software Engineer"], COUNTRY["IN"])

    # 95,000 x 1.00 x 0.28 = 26,600 USD / 0.0120 = 2,216,666.67 INR, in paise.
    assert reference.quantize(Decimal(1)) == Decimal(221_666_667)
    assert band.mid_minor == 222_000_000


def test_a_japanese_band_is_in_whole_yen_rounded_to_ten_thousand() -> None:
    band = band_for(Level.L1, ROLE["Software Engineer"], COUNTRY["JP"])

    # 70,000 x 0.62 = 43,400 USD / 0.0067 = 6,477,611.94 JPY.
    assert band.mid_minor == 6_480_000


def test_a_us_band_is_the_level_reference_times_the_role_multiplier() -> None:
    band = band_for(Level.L4, ROLE["Engineering Manager"], COUNTRY["US"])

    # 155,000 x 1.05 = 162,750 USD, rounded to the nearest 1,000.
    assert band == Band(min_minor=13_040_000, mid_minor=16_300_000, max_minor=19_560_000)


def test_band_min_and_max_are_0_8_and_1_2_times_the_mid() -> None:
    band = band_for(Level.L3, ROLE["Account Executive"], COUNTRY["DE"])

    assert band.min_minor == band.mid_minor * 8 // 10
    assert band.max_minor == band.mid_minor * 12 // 10


@pytest.mark.parametrize(
    ("code", "unit"),
    [("US", 100_000), ("IN", 1_000_000), ("JP", 10_000), ("DE", 100_000)],
)
def test_the_rounding_unit_is_in_minor_units_of_the_country_currency(code: str, unit: int) -> None:
    assert rounding_unit_minor(COUNTRY[code]) == unit


@pytest.mark.parametrize(
    ("amount", "rounded"),
    [
        (Decimal(2_500), 2_000),  # ties go to the even multiple
        (Decimal(3_500), 4_000),
        (Decimal("3499.99"), 3_000),
        (Decimal(1), 1_000),  # never below one unit
    ],
)
def test_amounts_round_half_even_to_a_multiple_of_the_unit(amount: Decimal, rounded: int) -> None:
    assert round_to_unit(amount, 1_000) == rounded


def test_uniform_draws_stay_in_range_with_four_decimals() -> None:
    rng = random.Random(1)

    draws = [draw_uniform(rng, (Decimal("0.02"), Decimal("0.06"))) for _ in range(1000)]

    assert all(Decimal("0.02") <= draw <= Decimal("0.06") for draw in draws)
    assert all(draw == draw.quantize(Decimal("0.0001")) for draw in draws)
    assert len(set(draws)) > 300


def test_the_same_seed_gives_the_same_draws() -> None:
    first, second = random.Random(7), random.Random(7)

    assert [draw_noise(first, 0.06, BOUNDS) for _ in range(5)] == [
        draw_noise(second, 0.06, BOUNDS) for _ in range(5)
    ]


def test_pay_noise_is_log_normal_with_median_one_and_spread_about_six_percent() -> None:
    rng = random.Random(42)

    noise = [draw_noise(rng, 0.06, BOUNDS) for _ in range(4000)]

    assert all(isinstance(value, Decimal) for value in noise)
    assert Decimal("0.99") < statistics.median(noise) < Decimal("1.01")
    spread = statistics.stdev(float(value.ln()) for value in noise)
    assert 0.05 < spread < 0.06  # 0.06, a little less after truncation


def test_pay_noise_never_leaves_its_bounds() -> None:
    rng = random.Random(3)

    noise = [draw_noise(rng, 0.06, BOUNDS) for _ in range(4000)]

    assert min(noise) >= Decimal("0.89")
    assert max(noise) <= Decimal("1.12")


def _every_band() -> list[tuple[CountrySpec, str, Decimal, int]]:
    """(country, department, unrounded reference, band mid) for all 1,360 bands."""
    return [
        (
            country,
            department.name,
            reference_minor(level, role, country),
            band_for(level, role, country).mid_minor,
        )
        for country in config.COUNTRIES
        for department in config.DEPARTMENTS
        for role in department.roles
        for level in role.levels
    ]


def test_noise_alone_never_flags_a_full_timer_in_any_band() -> None:
    low, high = config.PAY_NOISE_BOUNDS

    for country, _, reference, mid in _every_band():
        unit = rounding_unit_minor(country)
        lowest = Decimal(round_to_unit(reference * low, unit)) / mid
        highest = Decimal(round_to_unit(reference * high, unit)) / mid
        assert flag(lowest) == flag(highest) == PayEquityFlag.IN_BAND


def test_the_german_customer_success_gap_alone_flags_nobody() -> None:
    low, _ = config.PAY_NOISE_BOUNDS

    for country, department, reference, mid in _every_band():
        if (country.code, department) == ("DE", "Customer Success"):
            unit = rounding_unit_minor(country)
            base = round_to_unit(reference * low, unit)
            gapped = round_to_unit(base * config.PAY_GAP_FACTOR, unit)
            assert flag(Decimal(gapped) / mid) == PayEquityFlag.IN_BAND


def test_an_indian_full_timer_gets_hra_special_allowance_and_a_bonus_target() -> None:
    components = components_for(
        222_000_000,
        level=Level.L2,
        role=ROLE["Software Engineer"],
        country=COUNTRY["IN"],
        employment_type=FULL_TIME,
    )

    assert components == (
        ComponentAmount(ComponentType.ALLOWANCE, "HRA", 88_800_000),
        ComponentAmount(ComponentType.ALLOWANCE, "Special allowance", 22_200_000),
        ComponentAmount(ComponentType.BONUS_TARGET, "Target bonus", 17_760_000),
    )


def test_a_french_full_timer_gets_a_fixed_meal_allowance() -> None:
    components = components_for(
        5_000_000,
        level=Level.L1,
        role=ROLE["Accountant"],
        country=COUNTRY["FR"],
        employment_type=FULL_TIME,
    )

    assert components == (
        ComponentAmount(ComponentType.ALLOWANCE, "Meal", 150_000),
        ComponentAmount(ComponentType.BONUS_TARGET, "Target bonus", 250_000),
    )


@pytest.mark.parametrize(("code", "currency_minor"), [("GB", 120_000), ("DE", 120_000)])
def test_british_and_german_full_timers_get_a_transport_allowance(
    code: str, currency_minor: int
) -> None:
    components = components_for(
        6_000_000,
        level=Level.L3,
        role=ROLE["Recruiter"],
        country=COUNTRY[code],
        employment_type=FULL_TIME,
    )

    assert ComponentAmount(ComponentType.ALLOWANCE, "Transport", currency_minor) in components


def test_a_part_timer_gets_no_full_time_only_allowance_but_keeps_the_bonus_target() -> None:
    components = components_for(
        3_000_000,
        level=Level.L1,
        role=ROLE["Recruiter"],
        country=COUNTRY["GB"],
        employment_type=PART_TIME,
    )

    assert components == (ComponentAmount(ComponentType.BONUS_TARGET, "Target bonus", 150_000),)


def test_a_contractor_gets_no_allowance_and_no_bonus_target() -> None:
    components = components_for(
        222_000_000,
        level=Level.L2,
        role=ROLE["Software Engineer"],
        country=COUNTRY["IN"],
        employment_type=CONTRACTOR,
    )

    assert components == ()


def test_sales_roles_get_five_more_points_of_bonus_target() -> None:
    components = components_for(
        10_000_000,
        level=Level.L3,
        role=ROLE["Account Executive"],
        country=COUNTRY["US"],
        employment_type=FULL_TIME,
    )

    assert components == (ComponentAmount(ComponentType.BONUS_TARGET, "Target bonus", 1_500_000),)


def test_a_japanese_bonus_target_is_in_whole_yen() -> None:
    components = components_for(
        6_480_001,
        level=Level.L1,
        role=ROLE["Software Engineer"],
        country=COUNTRY["JP"],
        employment_type=FULL_TIME,
    )

    assert components == (ComponentAmount(ComponentType.BONUS_TARGET, "Target bonus", 324_000),)
