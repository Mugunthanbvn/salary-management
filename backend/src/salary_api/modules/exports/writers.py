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


def xlsx_bytes(title: str, header: Sequence[str], rows: Iterable[Sequence[CellValue]]) -> bytes:
    """A one-sheet workbook, written in openpyxl's streaming (write-only) mode.

    openpyxl writes text as a formula only when it starts with `=`, which escape_formula
    never leaves, so every text cell is a string cell (`t="s"`); numbers stay numbers and
    dates get a date format.
    """
    # Imported here, not at the top: openpyxl is slow to import (docs/19 section 6.3).
    from openpyxl import Workbook  # noqa: PLC0415

    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(title)
    sheet.append([escape_formula(name) for name in header])
    for row in rows:
        sheet.append([escape_formula(cell) if isinstance(cell, str) else cell for cell in row])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _csv_text(cell: CellValue) -> str:
    if cell is None:
        return ""
    if isinstance(cell, str):
        return escape_formula(cell)
    if isinstance(cell, date):
        return cell.isoformat()
    return str(cell)  # a number: plain digits, never escaped
