"""Accent- and case-insensitive search text (docs/glossary.md §8, docs/06-data-model.md §6.4).

SQLite's LIKE ignores case for ASCII only, so names are folded in Python, the same way for the
stored text and for the search term. Then `muller` finds `Müller` on every database.
"""

import unicodedata


def fold(text: str) -> str:
    """NFKD-normalise, strip combining marks (accents), then casefold: `Müller` -> `muller`."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return stripped.casefold()


def employee_search_text(first_name: str, last_name: str, employee_code: str, email: str) -> str:
    """What employee search matches against: the folded name, code and email."""
    return fold(f"{first_name} {last_name} {employee_code} {email}")
