"""The seed parameters match docs/12-seed-data.md sections 2-6 and 9-11 (data only)."""

from datetime import date
from decimal import Decimal

from salary_api.core.permissions import Role
from salary_api.domain.currency import SUPPORTED_CURRENCIES
from salary_api.domain.enums import EmploymentType, Level
from salary_api.modules.reference.models import JobFamily
from salary_api.seed import seed_config as config


def test_the_ten_countries_have_the_documented_currency_share_and_pay_factor() -> None:
    rows = [(c.code, c.currency, c.share, c.pay_factor) for c in config.COUNTRIES]

    assert rows == [
        ("US", "USD", 30, Decimal("1.00")),
        ("IN", "INR", 25, Decimal("0.28")),
        ("GB", "GBP", 10, Decimal("0.75")),
        ("DE", "EUR", 8, Decimal("0.75")),
        ("CA", "CAD", 6, Decimal("0.80")),
        ("FR", "EUR", 5, Decimal("0.68")),
        ("SG", "SGD", 5, Decimal("0.80")),
        ("AU", "AUD", 4, Decimal("0.80")),
        ("JP", "JPY", 4, Decimal("0.62")),
        ("BR", "BRL", 3, Decimal("0.30")),
    ]


def test_base_pay_rounds_to_ten_thousand_in_inr_and_jpy_and_a_thousand_elsewhere() -> None:
    rounding = {c.code: c.rounding_major for c in config.COUNTRIES}

    assert rounding == {
        "US": 1000,
        "IN": 10000,
        "GB": 1000,
        "DE": 1000,
        "CA": 1000,
        "FR": 1000,
        "SG": 1000,
        "AU": 1000,
        "JP": 10000,
        "BR": 1000,
    }


def test_every_country_but_singapore_has_a_faker_locale() -> None:
    locales = {c.code: c.faker_locale for c in config.COUNTRIES}

    assert locales == {
        "US": "en_US",
        "IN": "en_IN",
        "GB": "en_GB",
        "DE": "de_DE",
        "CA": "en_CA",
        "FR": "fr_FR",
        "SG": None,
        "AU": "en_AU",
        "JP": "ja_JP",
        "BR": "pt_BR",
    }


def test_departments_have_the_documented_shares() -> None:
    shares = [(d.name, d.share) for d in config.DEPARTMENTS]

    assert shares == [
        ("Engineering", 35),
        ("Sales", 15),
        ("Operations", 10),
        ("Customer Success", 10),
        ("Marketing", 8),
        ("Product", 6),
        ("Finance", 6),
        ("HR", 5),
        ("Legal", 5),
    ]


def test_there_are_35_job_roles_with_136_allowed_role_levels() -> None:
    roles = [role for department in config.DEPARTMENTS for role in department.roles]

    assert len(roles) == 35
    assert len({role.title for role in roles}) == 35
    assert sum(len(role.levels) for role in roles) == 136


def test_job_roles_have_the_documented_family_levels_and_multiplier() -> None:
    roles = {role.title: role for department in config.DEPARTMENTS for role in department.roles}

    engineering_manager = roles["Engineering Manager"]
    sdr = roles["Sales Development Representative"]

    assert (engineering_manager.family, engineering_manager.levels) == (
        JobFamily.ENGINEERING,
        (Level.L4, Level.L5, Level.L6),
    )
    assert engineering_manager.pay_multiplier == Decimal("1.05")
    assert (sdr.family, sdr.levels, sdr.pay_multiplier) == (
        JobFamily.SALES,
        (Level.L1, Level.L2),
        Decimal("0.70"),
    )
    assert roles["Product Designer"].family == JobFamily.DESIGN
    assert roles["Legal Counsel"].pay_multiplier == Decimal("1.10")


def test_role_weights_add_up_to_100_in_every_department_and_favour_individual_contributors() -> (
    None
):
    weights = {d.name: {r.title: r.weight for r in d.roles} for d in config.DEPARTMENTS}

    assert all(sum(roles.values()) == 100 for roles in weights.values())
    assert weights["Engineering"]["Software Engineer"] == 35


def test_levels_form_the_documented_pyramid_with_usd_bands_and_bonus_targets() -> None:
    levels = [
        (spec.level, spec.share, spec.reference_usd, spec.bonus_target_pct)
        for spec in config.LEVELS
    ]

    assert levels == [
        (Level.L1, 25, 70_000, Decimal("0.05")),
        (Level.L2, 30, 95_000, Decimal("0.08")),
        (Level.L3, 25, 125_000, Decimal("0.10")),
        (Level.L4, 12, 155_000, Decimal("0.15")),
        (Level.L5, 6, 190_000, Decimal("0.20")),
        (Level.L6, 2, 230_000, Decimal("0.25")),
    ]


def test_employment_types_are_90_6_4() -> None:
    assert config.EMPLOYMENT_TYPES == (
        (EmploymentType.FULL_TIME, 90),
        (EmploymentType.PART_TIME, 6),
        (EmploymentType.CONTRACTOR, 4),
    )


def test_allowances_follow_the_country_rules() -> None:
    rules = [
        (a.name, a.country_code, a.employment_types, a.percent_of_base, a.fixed_major)
        for a in config.ALLOWANCES
    ]
    full_and_part_time = (EmploymentType.FULL_TIME, EmploymentType.PART_TIME)
    full_time = (EmploymentType.FULL_TIME,)

    assert rules == [
        ("HRA", "IN", full_and_part_time, Decimal("0.40"), None),
        ("Special allowance", "IN", full_and_part_time, Decimal("0.10"), None),
        ("Meal", "FR", full_time, None, Decimal(1500)),
        ("Transport", "GB", full_time, None, Decimal(1200)),
        ("Transport", "DE", full_time, None, Decimal(1200)),
    ]


def test_sales_roles_get_five_more_bonus_points_and_contractors_get_no_bonus() -> None:
    assert Decimal("0.05") == config.SALES_BONUS_EXTRA
    assert EmploymentType.CONTRACTOR not in config.BONUS_EMPLOYMENT_TYPES


def test_the_fx_snapshot_has_a_rate_for_every_seeded_currency() -> None:
    currencies = {country.currency for country in config.COUNTRIES}

    assert set(config.FX_RATES) == currencies
    assert currencies <= SUPPORTED_CURRENCIES
    assert config.FX_RATES["USD"] == "1.0000"
    assert config.FX_RATES["INR"] == "0.0120"
    assert config.FX_RATES["JPY"] == "0.0067"
    assert (
        date(2026, 10, 1),
        "illustrative static snapshot",
    ) == (config.FX_AS_OF, config.FX_SOURCE)


def test_pay_noise_is_narrow_and_bounded_so_only_the_story_stands_out() -> None:
    assert config.PAY_NOISE_SIGMA == 0.06
    assert (Decimal("0.89"), Decimal("1.12")) == config.PAY_NOISE_BOUNDS


def test_dates_are_fixed_never_today() -> None:
    assert date(2026, 10, 1) == config.ANCHOR_DATE
    assert date(2026, 1, 1) == config.BAND_EFFECTIVE_FROM
    assert date(2015, 10, 1) == config.EARLIEST_HIRE_DATE


def test_singapore_names_are_a_curated_mix_of_about_40_first_and_30_last_names() -> None:
    first, last = config.SINGAPORE_FIRST_NAMES, config.SINGAPORE_LAST_NAMES

    assert len(first) >= 40
    assert len(last) >= 30
    assert len(set(first)) == len(first)
    assert len(set(last)) == len(last)
    assert {"Wei Ling", "Nur Aisyah", "Priya"} <= set(first)
    assert {"Tan", "Lim", "Ng", "Ramasamy"} <= set(last)


def test_the_three_demo_users_take_their_passwords_from_the_environment() -> None:
    users = [(u.email, u.full_name, u.role, u.password_env) for u in config.DEMO_USERS]

    assert users == [
        ("admin@acme.example", "Arun", Role.ADMIN, "SEED_ADMIN_PASSWORD"),
        ("hr@acme.example", "Hema", Role.HR_MANAGER, "SEED_HR_PASSWORD"),
        ("viewer@acme.example", "Farah", Role.VIEWER, "SEED_VIEWER_PASSWORD"),
    ]
