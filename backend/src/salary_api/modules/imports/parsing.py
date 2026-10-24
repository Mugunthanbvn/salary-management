"""Parse an uploaded CSV or XLSX file into raw rows (docs/11-import-export.md section 5.1).

Parsing is the only format-specific step: both parsers return the same `RawRow`s, so the
validator is written and tested once (ADR 0012). Pure: no database, no logging.
"""

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from salary_api.modules.imports.columns import TEMPLATE_COLUMNS

type Cell = str | None


@dataclass(frozen=True, slots=True)
class RawRow:
    """One data row: its spreadsheet row number (the header is row 1) and a text value, or
    None, for every template column. Values are not trimmed yet."""

    row: int
    values: Mapping[str, Cell]


def parse_csv(content: bytes, *, max_rows: int) -> list[RawRow]:
    """Rows of a UTF-8 CSV file (a BOM is allowed), comma-separated, quoted as RFC 4180."""
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    return _table(enumerate(reader, start=1), max_rows=max_rows)


def _table(records: Iterable[tuple[int, Sequence[Cell]]], *, max_rows: int) -> list[RawRow]:
    """The data rows under the header row, keyed by template column; blank rows skipped."""
    numbered = iter(records)
    _, header = next(numbered)
    columns = [_header_name(name) for name in header]
    rows: list[RawRow] = []
    for number, cells in numbered:
        found = dict(zip(columns, (_value(cell) for cell in cells), strict=False))
        if not any(value is not None for value in found.values()):
            continue
        rows.append(RawRow(row=number, values={c: found.get(c) for c in TEMPLATE_COLUMNS}))
    return rows


def _header_name(cell: Cell) -> str:
    return (cell or "").strip().lower()


def _value(cell: Cell) -> Cell:
    """None for an empty or blank cell, else the text as written."""
    return cell if cell is not None and cell.strip() else None
