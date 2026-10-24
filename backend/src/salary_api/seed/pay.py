"""The seed's pay maths: reference pay, pay bands, random factors and components.

docs/12-seed-data.md sections 5, 6 and 8. Amounts are integer minor units of the country's
currency; factors and FX rates are Decimal, and every result is rounded half-even.
"""

import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from salary_api.domain.currency import minor_unit_exponent
from salary_api.domain.enums import ComponentType, EmploymentType, Level
from salary_api.domain.rounding import round_half_even
from salary_api.modules.reference.models import JobFamily
from salary_api.seed import seed_config as config
from salary_api.seed.seed_config import AllowanceRule, CountrySpec, RoleSpec

_LEVELS: Final = {spec.level: spec for spec in config.LEVELS}
_GRID: Final = Decimal("0.0001")
"""Random factors have four decimals: plenty for pay rounded to 1,000 units."""

type Bounds = tuple[Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class Band:
    """A pay band in minor units of the country's currency."""

    min_minor: int
    mid_minor: int
    max_minor: int


@dataclass(frozen=True, slots=True)
class ComponentAmount:
    """An annual allowance or bonus target, in minor units of its record's currency."""

    type: ComponentType
    name: str
    amount_minor: int


def rounding_unit_minor(country: CountrySpec) -> int:
    """The multiple base pay is rounded to, in minor units (USD 1,000.00 is 100,000 cents)."""
    return country.rounding_major * 10 ** minor_unit_exponent(country.currency)


def round_to_unit(amount_minor: Decimal, unit_minor: int) -> int:
    """`amount_minor` rounded half-even to a multiple of `unit_minor`, and at least one unit."""
    return max(1, round_half_even(amount_minor / unit_minor)) * unit_minor


def reference_minor(level: Level, role: RoleSpec, country: CountrySpec) -> Decimal:
    """The pre-noise reference base in minor units, unrounded (section 5).

    reference_usd = level USD band x role multiplier x country factor, then / FX rate to USD.
    """
    usd = Decimal(_LEVELS[level].reference_usd) * role.pay_multiplier * country.pay_factor
    local_major = usd / Decimal(config.FX_RATES[country.currency])
    return local_major.scaleb(minor_unit_exponent(country.currency))


def band_for(level: Level, role: RoleSpec, country: CountrySpec) -> Band:
    """The band from the pre-noise reference: mid rounded like salaries, min 0.8 and max 1.2 x mid.

    It does not depend on the generated salaries, so a team-wide gap shows against it.
    """
    mid = round_to_unit(reference_minor(level, role, country), rounding_unit_minor(country))
    return Band(
        min_minor=round_half_even(mid * config.BAND_MIN_FACTOR),
        mid_minor=mid,
        max_minor=round_half_even(mid * config.BAND_MAX_FACTOR),
    )


def draw_uniform(rng: random.Random, bounds: Bounds) -> Decimal:
    """A factor from Uniform(low, high) on a 0.0001 grid, drawn as an integer step.

    Integer draws give the same factors on every platform (no float maths).
    """
    low, high = (bound.quantize(_GRID) for bound in bounds)
    steps = int((high - low) / _GRID)
    return low + rng.randint(0, steps) * _GRID


def draw_noise(rng: random.Random, sigma: float) -> Decimal:
    """exp(Normal(0, sigma)): log-normal pay noise with median 1.

    The normal draw is a float; it is cut to four decimals before Decimal.exp, so the last bit
    of a platform's float maths cannot change a salary.
    """
    return Decimal(rng.normalvariate(0.0, sigma)).quantize(_GRID).exp()


def components_for(
    base_minor: int,
    *,
    level: Level,
    role: RoleSpec,
    country: CountrySpec,
    employment_type: EmploymentType,
) -> tuple[ComponentAmount, ...]:
    """The allowances and bonus target of one salary record (section 6), in config order.

    Contractors get none. Fixed allowances are in the country's currency.
    """
    base = Decimal(base_minor)
    exponent = minor_unit_exponent(country.currency)
    components = [
        ComponentAmount(ComponentType.ALLOWANCE, rule.name, _allowance_minor(rule, base, exponent))
        for rule in config.ALLOWANCES
        if rule.country_code == country.code and employment_type in rule.employment_types
    ]
    if employment_type in config.BONUS_EMPLOYMENT_TYPES:
        bonus_pct = _LEVELS[level].bonus_target_pct
        if role.family == JobFamily.SALES:
            bonus_pct += config.SALES_BONUS_EXTRA
        components.append(
            ComponentAmount(
                ComponentType.BONUS_TARGET, config.BONUS_NAME, round_half_even(base * bonus_pct)
            )
        )
    return tuple(components)


def _allowance_minor(rule: AllowanceRule, base: Decimal, exponent: int) -> int:
    if rule.percent_of_base is not None:
        return round_half_even(base * rule.percent_of_base)
    if rule.fixed_major is not None:
        return round_half_even(rule.fixed_major.scaleb(exponent))
    raise ValueError(f"Allowance {rule.name} needs a percent of base or a fixed amount")
