"""Pay equity against pay bands: compa-ratio, flags, cohorts and department rollups.

The benchmark is the band midpoint for the employee's job role + level + country, not the
cohort's own median, so a team-wide gap shows up (docs/09-insights-pay-equity.md §3.8).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from salary_api.domain.constants import PAY_EQUITY_HIGH, PAY_EQUITY_LOW
from salary_api.domain.enums import EmploymentType, PayEquityFlag
from salary_api.domain.money import CurrencyMismatchError, Money


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


def compa_ratio(base: Money, band_mid: Money | None, employment_type: EmploymentType) -> CompaRatio:
    """An employee's annual base pay against the midpoint of their pay band.

    Only FULL_TIME employees get a ratio: part-time pay is not FTE-normalised, so comparing
    it with a full-time band would be wrong. That check comes before the band check.
    """
    if employment_type is not EmploymentType.FULL_TIME:
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
