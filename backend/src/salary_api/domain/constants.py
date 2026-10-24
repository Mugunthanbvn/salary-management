"""Named business thresholds (docs/glossary.md §3, docs/06 §5.1). Change them here only."""

from decimal import Decimal
from typing import Final

MAX_AMOUNT_DIGITS: Final = 15
MAX_AMOUNT_MINOR: Final = 10**MAX_AMOUNT_DIGITS - 1
"""The largest amount accepted as input, in minor units: 15 digits, far below BIGINT."""

MIN_GROUP_SIZE: Final = 5
"""Groups with fewer people are suppressed for callers without SALARY_READ (docs/09 §2.8)."""

PAY_EQUITY_LOW: Final = Decimal("0.80")
"""A compa-ratio below this is UNDERPAID; exactly 0.80 is IN_BAND."""

PAY_EQUITY_HIGH: Final = Decimal("1.20")
"""A compa-ratio above this is OVERPAID; exactly 1.20 is IN_BAND."""

ROLLUP_THRESHOLD: Final = Decimal("0.95")
"""A department whose median compa-ratio is below this is systematically below band."""
