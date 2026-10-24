"""Named thresholds hold the glossary §3 numbers, as int and exact Decimal (never float)."""

from datetime import timedelta
from decimal import Decimal

from salary_api.domain.constants import (
    DRY_RUN_TTL,
    MAX_ACTIVE_DRY_RUNS,
    MAX_AMOUNT_MINOR,
    MAX_IMPORT_ROWS,
    MAX_UPLOAD_BYTES,
    MAX_XLSX_UNCOMPRESSED_BYTES,
    MIN_GROUP_SIZE,
    PAY_EQUITY_HIGH,
    PAY_EQUITY_LOW,
    ROLLUP_THRESHOLD,
)


def test_small_group_threshold_is_five_people() -> None:
    assert MIN_GROUP_SIZE == 5


def test_amounts_have_at_most_15_digits_in_minor_units() -> None:
    assert MAX_AMOUNT_MINOR == 10**15 - 1


def test_pay_equity_thresholds_are_exact_decimals_from_the_glossary() -> None:
    thresholds = (PAY_EQUITY_LOW, PAY_EQUITY_HIGH, ROLLUP_THRESHOLD)

    assert thresholds == (Decimal("0.80"), Decimal("1.20"), Decimal("0.95"))
    assert all(type(threshold) is Decimal for threshold in thresholds)


def test_import_caps_hold_the_glossary_numbers() -> None:
    assert (
        4 * 1024 * 1024,
        10_000,
        timedelta(hours=24),
    ) == (MAX_UPLOAD_BYTES, MAX_IMPORT_ROWS, DRY_RUN_TTL)


def test_xlsx_uploads_expand_to_at_most_50_mb_and_a_user_keeps_3_dry_runs() -> None:
    assert (MAX_XLSX_UNCOMPRESSED_BYTES, MAX_ACTIVE_DRY_RUNS) == (50 * 1024 * 1024, 3)
