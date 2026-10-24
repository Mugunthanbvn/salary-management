"""Employee names per country and their work emails (docs/12-seed-data.md section 9).

Each country has its own name source seeded with `seed + country_index`, so names never draw
from the generator's main random stream: changing a name list cannot change any salary.
"""

import random
import re
from dataclasses import dataclass
from typing import Final, Protocol

from faker import Faker

from salary_api.domain.search import fold
from salary_api.seed import seed_config as config
from salary_api.seed.seed_config import CountrySpec, NameGroup

_NOT_ASCII_ALNUM: Final = re.compile(r"[^a-z0-9]")
_JAPANESE: Final = "ja_JP"


@dataclass(frozen=True, slots=True)
class PersonName:
    """A display name, and the Latin form the email is built from (romanized for Japan)."""

    first_name: str
    last_name: str
    email_first: str
    email_last: str


class NameSource(Protocol):
    def next_name(self) -> PersonName: ...


def name_source(country: CountrySpec, *, seed: int, country_index: int) -> NameSource:
    """The seeded name source of one country: Faker for its locale, or the curated lists."""
    if country.faker_locale is None:
        return _CuratedNames(config.SINGAPORE_NAME_GROUPS, random.Random(seed + country_index))
    # Unweighted: every listed name is equally likely, and generation is ~20x faster.
    faker = Faker(country.faker_locale, use_weighting=False)
    faker.seed_instance(seed + country_index)
    if country.faker_locale == _JAPANESE:
        return _JapaneseNames(faker)
    return _FakerNames(faker)


def ascii_slug(text: str) -> str:
    """`text` for an email local part: folded (no accents, lower case), ASCII letters and digits.

    `Müller` -> `muller`, `O'Connor` -> `oconnor`. Text with no Latin letters gives `x`.
    """
    return _NOT_ASCII_ALNUM.sub("", fold(text)) or "x"


class EmailBook:
    """Hands out unique work emails: `first.last.<last 4 digits of the code>@acme.example`.

    If that address is taken (same name, codes 10,000 apart), all six digits are used instead,
    which only that one code can produce.
    """

    def __init__(self) -> None:
        self._taken: set[str] = set()

    def email_for(self, name: PersonName, employee_code: str) -> str:
        digits = employee_code.removeprefix(config.EMPLOYEE_CODE_PREFIX)
        stem = f"{ascii_slug(name.email_first)}.{ascii_slug(name.email_last)}"
        email = f"{stem}.{digits[-4:]}@{config.EMAIL_DOMAIN}"
        if email in self._taken:
            email = f"{stem}.{digits}@{config.EMAIL_DOMAIN}"
        self._taken.add(email)
        return email


class _FakerNames:
    def __init__(self, faker: Faker) -> None:
        self._faker = faker

    def next_name(self) -> PersonName:
        first, last = self._faker.first_name(), self._faker.last_name()
        return PersonName(first, last, first, last)


class _JapaneseNames:
    """Kanji for display; the romanized reading for the email, so `sato` finds 佐藤."""

    def __init__(self, faker: Faker) -> None:
        self._faker = faker

    def next_name(self) -> PersonName:
        last_kanji, _, last_romanized = self._faker.last_name_pair()
        first_kanji, _, first_romanized = self._faker.first_name_pair()
        return PersonName(first_kanji, last_kanji, first_romanized, last_romanized)


class _CuratedNames:
    """Singapore: pick an origin by weight, then a first and a last name of that origin."""

    def __init__(self, groups: tuple[NameGroup, ...], rng: random.Random) -> None:
        self._groups = groups
        self._weights = [group.weight for group in groups]
        self._rng = rng

    def next_name(self) -> PersonName:
        group = self._rng.choices(self._groups, weights=self._weights)[0]
        first = self._rng.choice(group.first_names)
        last = self._rng.choice(group.last_names)
        return PersonName(first, last, first, last)
