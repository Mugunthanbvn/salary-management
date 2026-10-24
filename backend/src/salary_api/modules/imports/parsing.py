"""Parse an uploaded CSV or XLSX file into raw rows (docs/11-import-export.md section 5.1).

Parsing is the only format-specific step: both parsers return the same `RawRow`s, so the
validator is written and tested once (ADR 0012). Pure: no database, no logging.
"""

import csv
import io
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from salary_api.modules.imports.columns import REQUIRED_COLUMNS, TEMPLATE_COLUMNS

type Cell = str | None

NOT_UTF8 = "The file is not UTF-8. In Excel choose File > Save As > 'CSV UTF-8 (Comma delimited)'."


class UnreadableFile(ValueError):
    """The upload cannot be read as an import file (400 bad-request). The message says why."""


class HeaderMismatch(UnreadableFile):
    """The header row does not match the template: unknown, missing or repeated columns."""


class TooManyRows(ValueError):
    """The file has more data rows than `limit`."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"The file has more than {limit} employee rows.")
        self.limit = limit


@dataclass(frozen=True, slots=True)
class RawRow:
    """One data row: its spreadsheet row number (the header is row 1) and a text value, or
    None, for every template column. Values are not trimmed yet."""

    row: int
    values: Mapping[str, Cell]


def parse_csv(content: bytes, *, max_rows: int) -> list[RawRow]:
    """Rows of a UTF-8 CSV file (a BOM is allowed), comma-separated, quoted as RFC 4180."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UnreadableFile(NOT_UTF8) from None
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    return _table(_csv_records(reader), max_rows=max_rows)


def _csv_records(reader: Iterator[list[str]]) -> Iterator[tuple[int, Sequence[Cell]]]:
    """Numbered records. A multi-line quoted value stays one row, as Excel shows it."""
    number = 0
    while True:
        number += 1
        try:
            cells = next(reader)
        except StopIteration:
            return
        except csv.Error as error:
            raise UnreadableFile(f"Row {number} could not be read: {error}.") from None
        yield number, cells


def _table(records: Iterable[tuple[int, Sequence[Cell]]], *, max_rows: int) -> list[RawRow]:
    """The data rows under the header row, keyed by template column; blank rows skipped."""
    numbered = iter(records)
    first = next(numbered, None)
    if first is None:
        raise UnreadableFile("The file is empty: it needs a header row and employee rows.")
    columns = _columns(first[1])
    rows: list[RawRow] = []
    for number, cells in numbered:
        values = _row_values(number, columns, cells)
        if values is None:
            continue
        if len(rows) == max_rows:
            raise TooManyRows(max_rows)
        rows.append(RawRow(row=number, values=values))
    if not rows:
        raise UnreadableFile("The file has a header row but no employee rows.")
    return rows


def _columns(header: Sequence[Cell]) -> list[str]:
    """The template column of each position ("" for a column with no header).

    Raises HeaderMismatch naming every unknown, repeated and missing column.
    """
    columns = [(cell or "").strip().lower() for cell in header]
    named = [column for column in columns if column]
    problems: list[str] = []
    if len(named) == 1 and ";" in named[0]:
        problems.append("Separate the columns with commas, not semicolons.")
    else:
        unknown = [column for column in named if column not in TEMPLATE_COLUMNS]
        if unknown:
            problems.append(f"Unknown column{_s(unknown)}: {', '.join(unknown)}.")
        repeated = sorted({column for column in named if named.count(column) > 1})
        problems += [f"The column {column} appears more than once." for column in repeated]
    missing = [column for column in TEMPLATE_COLUMNS if column in REQUIRED_COLUMNS - set(named)]
    if missing:
        problems.append(f"Missing required column{_s(missing)}: {', '.join(missing)}.")
    if problems:
        raise HeaderMismatch(" ".join(problems))
    return columns


def _row_values(
    number: int, columns: Sequence[str], cells: Sequence[Cell]
) -> dict[str, Cell] | None:
    """The row's value for every template column, or None for a blank row."""
    values: dict[str, Cell] = dict.fromkeys(TEMPLATE_COLUMNS)
    blank = True
    for position, cell in enumerate(cells):
        value = _value(cell)
        if value is None:
            continue
        column = columns[position] if position < len(columns) else ""
        if not column:
            raise UnreadableFile(
                f"Row {number} has a value in column {_letter(position)}, which has no header. "
                "Put values that contain commas in double quotes."
            )
        values[column] = value
        blank = False
    return None if blank else values


def _value(cell: Cell) -> Cell:
    """None for an empty or blank cell, else the text as written."""
    return cell if cell is not None and cell.strip() else None


def _letter(position: int) -> str:
    """The spreadsheet column letter of a 0-based position: 0 is A, 26 is AA."""
    letters = ""
    number = position + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _s(items: Sequence[object]) -> str:
    return "s" if len(items) > 1 else ""
