"""The CSV parser turns an upload into raw rows keyed by template column (docs/11 section 5.1)."""

import pytest

from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.imports.parsing import RawRow, parse_csv

HEADER = "employee_code,first_name,last_name,email,job_role,level,employment_type,country,hire_date"


def _row(row: int, **values: str) -> RawRow:
    """A raw row with every template column, None where the file had no value."""
    return RawRow(row=row, values={column: values.get(column) for column in TEMPLATE_COLUMNS})


def _csv(*lines: str, bom: bool = False) -> bytes:
    return ("﻿" if bom else "").encode() + "\r\n".join(lines).encode("utf-8")


@pytest.mark.parametrize("bom", [False, True])
def test_csv_rows_are_keyed_by_template_column_with_or_without_a_bom(bom: bool) -> None:
    content = _csv(
        HEADER, "ACME-010001,Jürgen,Müller,j@acme.example,QA,L2,FULL_TIME,DE,2022-04-01", bom=bom
    )

    rows = parse_csv(content, max_rows=10)

    assert rows == [
        _row(
            2,
            employee_code="ACME-010001",
            first_name="Jürgen",
            last_name="Müller",
            email="j@acme.example",
            job_role="QA",
            level="L2",
            employment_type="FULL_TIME",
            country="DE",
            hire_date="2022-04-01",
        )
    ]


def test_csv_headers_are_case_insensitive_trimmed_and_in_any_order() -> None:
    names = [" Hire_Date ", "COUNTRY", "Employment_Type", "level", "job_role", "EMAIL"]
    header = ",".join([*names, "last_name", "first_name", "employee_code"])
    content = _csv(header, "2022-04-01,DE,FULL_TIME,L2,QA,j@acme.example,Müller,Jürgen,ACME-010001")

    [row] = parse_csv(content, max_rows=10)

    assert (row.values["employee_code"], row.values["hire_date"]) == ("ACME-010001", "2022-04-01")


def test_blank_lines_are_skipped_but_still_count_as_spreadsheet_rows() -> None:
    line = "ACME-01000{n},A,B,a{n}@acme.example,QA,L2,FULL_TIME,DE,2022-04-01"
    content = _csv(HEADER, line.format(n=1), "", ",,,,,,,,", line.format(n=2), "")

    rows = parse_csv(content, max_rows=10)

    assert [row.row for row in rows] == [2, 5]


def test_quoted_values_may_hold_commas_quotes_and_line_breaks() -> None:
    content = _csv(
        HEADER,
        'ACME-010001,"Mary, Jr","O""Brien","m@acme.example","Line\r\nbreak",'
        "L2,FULL_TIME,DE,2022-04-01",
        "ACME-010002,A,B,b@acme.example,QA,L2,FULL_TIME,DE,2022-04-01",
    )

    first, second = parse_csv(content, max_rows=10)

    assert (first.values["first_name"], first.values["last_name"]) == ("Mary, Jr", 'O"Brien')
    assert first.values["job_role"] == "Line\r\nbreak"
    assert second.row == 3  # Excel shows a multi-line cell in one row


def test_empty_cells_and_absent_optional_columns_are_none() -> None:
    content = _csv(
        HEADER + ",bonus_target", "ACME-010001,A,B,a@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,  "
    )

    [row] = parse_csv(content, max_rows=10)

    assert (row.values["bonus_target"], row.values["currency"]) == (None, None)


def test_values_keep_their_spaces_for_the_validator_to_trim() -> None:
    content = _csv(HEADER, " ACME-010001 ,A,B,a@acme.example,QA,L2,FULL_TIME,DE,2022-04-01")

    [row] = parse_csv(content, max_rows=10)

    assert row.values["employee_code"] == " ACME-010001 "
