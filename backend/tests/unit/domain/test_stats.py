"""Statistics over integer minor amounts (docs/09-insights-pay-equity.md §2.7, ADR 0007)."""

from salary_api.domain.stats import InsufficientData, Summary, summarize


def test_an_empty_input_is_insufficient_data_not_zero_or_an_error() -> None:
    result = summarize([])

    assert result == InsufficientData()


def test_a_single_value_is_every_statistic() -> None:
    result = summarize([5200000])

    assert result == Summary(
        count=1,
        min=5200000,
        p25=5200000,
        median=5200000,
        mean=5200000,
        p75=5200000,
        max=5200000,
        sum=5200000,
    )
