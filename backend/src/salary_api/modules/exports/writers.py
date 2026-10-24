"""Write rows as CSV or XLSX files that are safe to open (docs/11-import-export.md section 6).

Every text cell goes through escape_formula. CSV is UTF-8 with a BOM, so Excel shows
`Müller` correctly on a double-click; XLSX text cells are typed as strings, numbers as
numbers and dates as dates.
"""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal

from salary_api.modules.exports.csv_safety import escape_formula

type CellValue = str | int | Decimal | date | None

BOM = "﻿"


def csv_bytes(header: Sequence[str], rows: Iterable[Sequence[CellValue]]) -> bytes:
    """A UTF-8 CSV with a BOM, CRLF line ends, quoted as RFC 4180."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([escape_formula(name) for name in header])
    writer.writerows([_csv_text(cell) for cell in row] for row in rows)
    return (BOM + buffer.getvalue()).encode("utf-8")


def _csv_text(cell: CellValue) -> str:
    if cell is None:
        return ""
    if isinstance(cell, str):
        return escape_formula(cell)
    if isinstance(cell, date):
        return cell.isoformat()
    return str(cell)  # a number: plain digits, never escaped
