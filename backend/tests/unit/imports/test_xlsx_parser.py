"""The XLSX parser reads values only and gives the same rows as the CSV parser (docs/11 5.1)."""

from datetime import date, datetime
from pathlib import Path

import pytest

from salary_api.modules.imports.parsing import (
    HeaderMismatch,
    TooManyRows,
    UnreadableFile,
    parse_csv,
    parse_xlsx,
)
from tests.spreadsheets import FULL_HEADER, replace_in_sheets, xlsx_bytes, zip_bytes

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
LIMIT = 50 * 1024 * 1024


def _employee(**cells: object) -> list[object]:
    """One template row of typed cells; columns not given are empty."""
    row: dict[str, object] = {
        "employee_code": "ACME-010001",
        "first_name": "Lena",
        "last_name": "Müller",
        "email": "lena@acme.example",
        "job_role": "Software Engineer",
        "level": "L2",
        "employment_type": "FULL_TIME",
        "country": "DE",
        "hire_date": date(2022, 4, 1),
        "base_salary": 52000,
    }
    row |= cells
    return [row.get(column) for column in FULL_HEADER]


def _parse(content: bytes, *, max_rows: int = 10, limit: int = LIMIT) -> list[dict[str, object]]:
    return [
        dict(raw.values)
        for raw in parse_xlsx(content, max_rows=max_rows, max_uncompressed_bytes=limit)
    ]


def test_the_xlsx_golden_file_parses_to_the_same_rows_as_the_csv_golden_file() -> None:
    from_csv = parse_csv((FIXTURES / "import_sample.csv").read_bytes(), max_rows=10)

    from_xlsx = parse_xlsx(
        (FIXTURES / "import_sample.xlsx").read_bytes(), max_rows=10, max_uncompressed_bytes=LIMIT
    )

    assert from_xlsx == from_csv
    assert len(from_xlsx) == 4


@pytest.mark.parametrize(
    ("cell", "text"),
    [
        (52000, "52000"),
        (4160.5, "4160.5"),
        (1234.56, "1234.56"),  # the float's shortest repr, not 1234.559999...
        (0.1, "0.1"),
        (1e16, "10000000000000000"),
        (True, "TRUE"),
        (date(2022, 4, 1), "2022-04-01"),
        (datetime(2022, 4, 1, 0, 0), "2022-04-01"),
        (datetime(2022, 4, 1, 10, 30), "2022-04-01T10:30:00"),
        (" spaced ", " spaced "),
    ],
)
def test_cells_become_text_without_float_drift(cell: object, text: str) -> None:
    [row] = _parse(xlsx_bytes([FULL_HEADER, _employee(bonus_target=cell)]))

    assert row["bonus_target"] == text


def test_the_employees_sheet_is_read_when_the_workbook_has_several() -> None:
    content = xlsx_bytes([FULL_HEADER, _employee()], sheets_before=["Notes", "Totals"])

    [row] = _parse(content)

    assert row["employee_code"] == "ACME-010001"


def test_the_first_sheet_is_read_when_no_sheet_is_called_employees() -> None:
    [row] = _parse(xlsx_bytes([FULL_HEADER, _employee()], title="Q4 hires"))

    assert row["employee_code"] == "ACME-010001"


def test_a_formula_cell_is_read_as_its_saved_value() -> None:
    content = xlsx_bytes([FULL_HEADER, _employee(bonus_target="=1000+160")])
    content = replace_in_sheets(content, "<f>1000+160</f><v />", "<f>1000+160</f><v>1160</v>")

    [row] = _parse(content)

    assert row["bonus_target"] == "1160"


def test_a_formula_without_a_saved_value_is_refused_with_its_cell() -> None:
    content = xlsx_bytes([FULL_HEADER, _employee(bonus_target="=1000+160")])

    with pytest.raises(UnreadableFile, match="Cell L2 has a formula without a saved value"):
        _parse(content)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"employee_code,first_name\r\n", id="a CSV renamed to .xlsx"),
        pytest.param(zip_bytes({"notes.txt": b"hello"}), id="a zip that is no workbook"),
        pytest.param(b"PK\x03\x04 broken", id="a damaged zip"),
    ],
)
def test_a_file_that_is_not_a_workbook_is_refused(content: bytes) -> None:
    with pytest.raises(UnreadableFile, match="not an Excel workbook"):
        _parse(content)


def test_a_workbook_that_expands_past_the_limit_is_refused_before_it_is_read() -> None:
    content = xlsx_bytes([FULL_HEADER, _employee()])

    with pytest.raises(UnreadableFile, match="expands to more than"):
        _parse(content, limit=1_000)


def test_the_xlsx_header_follows_the_template_rules() -> None:
    header = [*FULL_HEADER[:-1], "emial"]

    with pytest.raises(HeaderMismatch, match="Unknown column: emial"):
        _parse(xlsx_bytes([header, _employee()]))


def test_more_xlsx_rows_than_the_cap_are_refused() -> None:
    content = xlsx_bytes([FULL_HEADER, _employee(), _employee(), _employee()])

    with pytest.raises(TooManyRows):
        _parse(content, max_rows=2)
