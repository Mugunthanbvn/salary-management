"""Seeded names per country and ASCII emails (docs/12-seed-data.md section 9)."""

import pytest

from salary_api.seed import seed_config as config
from salary_api.seed.names import EmailBook, PersonName, ascii_slug, name_source

COUNTRY = {country.code: country for country in config.COUNTRIES}


def _names(code: str, seed: int = 42, count: int = 200) -> list[PersonName]:
    index = config.COUNTRIES.index(COUNTRY[code])
    source = name_source(COUNTRY[code], seed=seed, country_index=index)
    return [source.next_name() for _ in range(count)]


@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("Müller", "muller"),
        ("François", "francois"),
        ("Straße", "strasse"),
        ("da Conceição", "daconceicao"),
        ("O'Connor-Smith", "oconnorsmith"),
        ("Wei Ling", "weiling"),
        ("佐藤", "x"),  # nothing Latin left: a placeholder, never an empty local part
    ],
)
def test_names_fold_to_lowercase_ascii_for_emails(text: str, slug: str) -> None:
    assert ascii_slug(text) == slug


def test_an_email_is_first_last_and_the_last_four_digits_of_the_code() -> None:
    book = EmailBook()

    email = book.email_for(PersonName("José", "da Silva", "José", "da Silva"), "ACME-000042")

    assert email == "jose.dasilva.0042@acme.example"


def test_a_repeated_name_and_last_four_digits_falls_back_to_all_six_digits() -> None:
    book = EmailBook()
    name = PersonName("Anna", "Schmidt", "Anna", "Schmidt")
    book.email_for(name, "ACME-000001")

    email = book.email_for(name, "ACME-010001")

    assert email == "anna.schmidt.010001@acme.example"


def test_the_same_seed_gives_the_same_names() -> None:
    assert _names("DE") == _names("DE")


def test_another_seed_gives_other_names() -> None:
    assert _names("DE", seed=42) != _names("DE", seed=43)


def test_german_names_include_accented_letters() -> None:
    names = _names("DE")

    assert any(not (name.first_name + name.last_name).isascii() for name in names)


def test_japanese_names_show_in_kanji_with_romanized_email_parts() -> None:
    names = _names("JP", count=20)

    assert all(not name.last_name.isascii() for name in names)
    assert all((name.email_first + name.email_last).isascii() for name in names)
    assert all(ascii_slug(name.email_last) != "x" for name in names)


def test_singapore_names_take_first_and_last_name_from_one_origin() -> None:
    names = _names("SG", count=500)

    groups = config.SINGAPORE_NAME_GROUPS
    for name in names:
        assert any(
            name.first_name in group.first_names and name.last_name in group.last_names
            for group in groups
        )
    origins = {
        group.origin for name in names for group in groups if name.last_name in group.last_names
    }
    assert origins == {"Chinese", "Malay", "Indian"}
