"""Search folding (docs/glossary.md section 8, docs/06-data-model.md section 6.4)."""

import pytest

from salary_api.domain.search import employee_search_text, fold


@pytest.mark.parametrize(
    ("text", "folded"),
    [
        pytest.param("Müller", "muller", id="accent stripped"),
        pytest.param("JOSÉ", "jose", id="upper case and accent"),
        pytest.param("Straße", "strasse", id="sharp s casefolds to ss"),
        pytest.param("ﬁona", "fiona", id="compatibility ligature"),
        pytest.param("Ångström", "angstrom", id="ring above and diaeresis"),
        pytest.param("佐藤", "佐藤", id="non-Latin script kept"),
        pytest.param("ACME-004217", "acme-004217", id="employee code"),
    ],
)
def test_fold_normalises_strips_accents_and_casefolds(text: str, folded: str) -> None:
    assert fold(text) == folded


def test_a_folded_search_term_finds_the_accented_name() -> None:
    assert fold("müller") in employee_search_text("Lena", "Müller", "ACME-000001", "l@a.example")


def test_employee_search_text_folds_name_code_and_email_in_that_order() -> None:
    text = employee_search_text("José", "Müller", "ACME-004217", "jose.mueller@acme.example")

    assert text == "jose muller acme-004217 jose.mueller@acme.example"
