"""Pay equity against pay bands: compa-ratio, flags, cohorts and department rollups.

The benchmark is the band midpoint for the employee's job role + level + country, not the
cohort's own median, so a team-wide gap shows up (docs/09-insights-pay-equity.md §3.8).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from salary_api.domain.enums import EmploymentType
from salary_api.domain.money import Money


class NoCompaRatioReason(StrEnum):
    """Why an employee has no compa-ratio."""

    NO_BAND = "no_band"


@dataclass(frozen=True, slots=True)
class CompaRatio:
    """Base pay ÷ band midpoint, at full Decimal precision (round only for display).

    `value` is None when no ratio can be computed, and `reason` then says why.
    """

    value: Decimal | None
    reason: NoCompaRatioReason | None = None


def compa_ratio(base: Money, band_mid: Money | None, employment_type: EmploymentType) -> CompaRatio:
    """An employee's annual base pay against the midpoint of their pay band."""
    if band_mid is None:
        return CompaRatio(None, NoCompaRatioReason.NO_BAND)
    return CompaRatio(Decimal(base.amount_minor) / Decimal(band_mid.amount_minor))
