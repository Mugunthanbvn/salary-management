"""Statistics over integer minor amounts (docs/09-insights-pay-equity.md §2.7, ADR 0007)."""

from salary_api.domain.stats import InsufficientData, summarize


def test_an_empty_input_is_insufficient_data_not_zero_or_an_error() -> None:
    result = summarize([])

    assert result == InsufficientData()
