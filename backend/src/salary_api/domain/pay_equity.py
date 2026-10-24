"""Pay equity against pay bands: compa-ratio, flags, cohorts and department rollups.

The benchmark is the band midpoint for the employee's job role + level + country, not the
cohort's own median, so a team-wide gap shows up (docs/09-insights-pay-equity.md §3.8).
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Self

from salary_api.domain.constants import PAY_EQUITY_HIGH, PAY_EQUITY_LOW, ROLLUP_THRESHOLD
from salary_api.domain.enums import EmploymentType, Level, PayEquityFlag
from salary_api.domain.money import CurrencyMismatchError, Money
from salary_api.domain.stats import Summary, mean, median


class NoCompaRatioReason(StrEnum):
    """Why an employee has no compa-ratio."""

    NOT_FULL_TIME = "not_full_time"
    NO_BAND = "no_band"


@dataclass(frozen=True, slots=True)
class CompaRatio:
    """Base pay ÷ band midpoint, at full Decimal precision (round only for display).

    `value` is None when no ratio can be computed, and `reason` then says why.
    """

    value: Decimal | None
    reason: NoCompaRatioReason | None = None


@dataclass(frozen=True, slots=True, order=True)
class CohortKey:
    """Peers doing the same job at the same level in the same labour market (and currency)."""

    job_role_id: int
    level: Level
    country_code: str


@dataclass(frozen=True, slots=True)
class EmployeePay:
    """What pay equity needs to know about one employee. `band_mid` is None with no band."""

    department_id: int
    job_role_id: int
    level: Level
    country_code: str
    employment_type: EmploymentType
    base: Money
    band_mid: Money | None

    @property
    def cohort(self) -> CohortKey:
        return CohortKey(self.job_role_id, self.level, self.country_code)


def compa_ratio(base: Money, band_mid: Money | None, employment_type: EmploymentType) -> CompaRatio:
    """An employee's annual base pay against the midpoint of their pay band.

    Only FULL_TIME employees get a ratio: part-time pay is not FTE-normalised, so comparing
    it with a full-time band would be wrong. That check comes before the band check.
    """
    if employment_type != EmploymentType.FULL_TIME:  # equality, so a plain DB string works
        return CompaRatio(None, NoCompaRatioReason.NOT_FULL_TIME)
    if band_mid is None:
        return CompaRatio(None, NoCompaRatioReason.NO_BAND)
    if band_mid.currency != base.currency:
        raise CurrencyMismatchError(base.currency, band_mid.currency)
    return CompaRatio(Decimal(base.amount_minor) / Decimal(band_mid.amount_minor))


def flag(ratio: Decimal) -> PayEquityFlag:
    """UNDERPAID below 0.80, OVERPAID above 1.20, IN_BAND between them (edges included).

    Pass the unrounded ratio: 0.79999 is UNDERPAID even though it displays as 0.80.
    """
    if ratio < PAY_EQUITY_LOW:
        return PayEquityFlag.UNDERPAID
    if ratio > PAY_EQUITY_HIGH:
        return PayEquityFlag.OVERPAID
    return PayEquityFlag.IN_BAND


@dataclass(frozen=True, slots=True)
class CompaRatioSummary:
    """The compa-ratios of one group (a department or a cohort), all unrounded.

    Round only for display. Field names match the API (docs/07 §8.10).
    """

    count: int
    median_compa_ratio: Decimal
    mean_compa_ratio: Decimal
    underpaid_count: int
    overpaid_count: int

    @property
    def pct_below_band(self) -> Decimal:
        """The share of the group that is UNDERPAID, from 0 to 1 (0.29 means 29 %)."""
        return Decimal(self.underpaid_count) / self.count

    @classmethod
    def of(cls, ratios: Iterable[Decimal]) -> Self:
        """Summarise a group's compa-ratios. Needs at least one ratio (ValueError otherwise)."""
        collected = list(ratios)
        flags = Counter(flag(ratio) for ratio in collected)
        return cls(
            count=len(collected),
            median_compa_ratio=median(collected),
            mean_compa_ratio=mean(collected),
            underpaid_count=flags[PayEquityFlag.UNDERPAID],
            overpaid_count=flags[PayEquityFlag.OVERPAID],
        )


@dataclass(frozen=True, slots=True)
class DepartmentRollup:
    """One department in one country (docs/07 §8.10 `view=departments`)."""

    department_id: int
    country_code: str
    ratios: CompaRatioSummary

    @property
    def below_threshold(self) -> bool:
        """Systematically below band: the unrounded median is under 0.95 (0.95 itself is not)."""
        return self.ratios.median_compa_ratio < ROLLUP_THRESHOLD


def department_rollup(employees: Iterable[EmployeePay]) -> list[DepartmentRollup]:
    """Compa-ratios summarised per department x country, sorted by department then country.

    Employees without a compa-ratio (no band, or not full-time) are left out entirely.
    """
    ratios: defaultdict[tuple[int, str], list[Decimal]] = defaultdict(list)
    for pay in employees:
        ratio = compa_ratio(pay.base, pay.band_mid, pay.employment_type).value
        if ratio is not None:
            ratios[pay.department_id, pay.country_code].append(ratio)
    return [
        DepartmentRollup(department_id, country_code, CompaRatioSummary.of(values))
        for (department_id, country_code), values in sorted(ratios.items())
    ]


@dataclass(frozen=True, slots=True)
class CohortRollup:
    """One cohort (docs/07 §8.10 `view=cohorts`): base pay spread and compa-ratios.

    `base` is in minor units of `currency`. The band itself comes from pay_bands.
    """

    cohort: CohortKey
    currency: str
    base: Summary
    ratios: CompaRatioSummary


def cohort_rollup(employees: Iterable[EmployeePay]) -> list[CohortRollup]:
    """Base pay and compa-ratios per job role x level x country, sorted by that key.

    Only employees with a compa-ratio count, so a cohort without a band is not listed.
    """
    members: defaultdict[CohortKey, list[tuple[Money, Decimal]]] = defaultdict(list)
    for pay in employees:
        ratio = compa_ratio(pay.base, pay.band_mid, pay.employment_type).value
        if ratio is not None:
            members[pay.cohort].append((pay.base, ratio))
    return [_cohort_rollup(cohort, group) for cohort, group in sorted(members.items())]


def _cohort_rollup(cohort: CohortKey, group: list[tuple[Money, Decimal]]) -> CohortRollup:
    currency = group[0][0].currency
    for base, _ in group:
        if base.currency != currency:
            raise CurrencyMismatchError(currency, base.currency)
    return CohortRollup(
        cohort=cohort,
        currency=currency,
        base=Summary.of(base.amount_minor for base, _ in group),
        ratios=CompaRatioSummary.of(ratio for _, ratio in group),
    )
