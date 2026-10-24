"""Neutralise spreadsheet formulas in exported text (docs/08-security-rbac.md section 7.1).

Excel, LibreOffice and Google Sheets run a cell that starts with `=`, `+`, `-` or `@` as a
formula, and some also after a tab or carriage return. A name such as
`=HYPERLINK("http://evil","click")` would run when finance opens the export. OWASP's fix:
start such text with a single quote, which shows the text as written.
"""

from typing import Final

FORMULA_STARTS: Final = ("=", "+", "-", "@", "\t", "\r")


def escape_formula(text: str) -> str:
    """`text` with a leading `'` if a spreadsheet could read it as a formula."""
    return "'" + text if text.startswith(FORMULA_STARTS) else text
