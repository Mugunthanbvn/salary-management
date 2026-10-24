"""Exported text never starts a spreadsheet formula (docs/08 section 7.1, OWASP CSV injection)."""

import pytest

from salary_api.modules.exports.csv_safety import escape_formula


@pytest.mark.parametrize(
    "text",
    [
        "=1+1",
        '=HYPERLINK("http://evil","click")',
        "+44 20 7946 0000",
        "-2+3",
        "@SUM(A1)",
        "\tTabbed",
        "\rReturn",
    ],
)
def test_text_starting_with_a_formula_character_gets_a_leading_quote(text: str) -> None:
    assert escape_formula(text) == "'" + text


@pytest.mark.parametrize(
    "text", ["Müller", "a=b", "O'Brien", "", " =spaced first", "ACME-010001", "2026-10-01"]
)
def test_other_text_is_unchanged(text: str) -> None:
    assert escape_formula(text) == text
