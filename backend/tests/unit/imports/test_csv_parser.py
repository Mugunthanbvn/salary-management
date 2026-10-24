"""The CSV parser turns an upload into raw rows keyed by template column (docs/11 section 5.1)."""

import pytest

from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.imports.parsing import (
    HeaderMismatch,
    RawRow,
    TooManyRows,
    UnreadableFile,
    parse_csv,
)

HEADER = "employee_code,first_name,last_name,email,job_role,level,employment_type,country,hire_date"
HEADER += ",base_salary"


def _row(row: int, **values: str) -> RawRow:
    """A raw row with every template column, None where the file had no value."""
    return RawRow(row=row, values={column: values.get(column) for column in TEMPLATE_COLUMNS})


def _csv(*lines: str, bom: bool = False) -> bytes:
    return ("﻿" if bom else "").encode() + "\r\n".join(lines).encode("utf-8")


@pytest.mark.parametrize("bom", [False, True])
def test_csv_rows_are_keyed_by_template_column_with_or_without_a_bom(bom: bool) -> None:
    content = _csv(
        HEADER,
        "ACME-010001,Jürgen,Müller,j@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,52000",
        bom=bom,
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
            base_salary="52000",
        )
    ]


def test_csv_headers_are_case_insensitive_trimmed_and_in_any_order() -> None:
    names = [
        "Base_Salary",
        " Hire_Date ",
        "COUNTRY",
        "Employment_Type",
        "level",
        "job_role",
        "EMAIL",
    ]
    header = ",".join([*names, "last_name", "first_name", "employee_code"])
    content = _csv(
        header, "52000,2022-04-01,DE,FULL_TIME,L2,QA,j@acme.example,Müller,Jürgen,ACME-010001"
    )

    [row] = parse_csv(content, max_rows=10)

    assert (row.values["employee_code"], row.values["hire_date"]) == ("ACME-010001", "2022-04-01")


def test_blank_lines_are_skipped_but_still_count_as_spreadsheet_rows() -> None:
    line = "ACME-01000{n},A,B,a{n}@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,52000"
    content = _csv(HEADER, line.format(n=1), "", ",,,,,,,,", line.format(n=2), "")

    rows = parse_csv(content, max_rows=10)

    assert [row.row for row in rows] == [2, 5]


def test_quoted_values_may_hold_commas_quotes_and_line_breaks() -> None:
    content = _csv(
        HEADER,
        'ACME-010001,"Mary, Jr","O""Brien","m@acme.example","Line\r\nbreak",'
        "L2,FULL_TIME,DE,2022-04-01,52000",
        "ACME-010002,A,B,b@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,52000",
    )

    first, second = parse_csv(content, max_rows=10)

    assert (first.values["first_name"], first.values["last_name"]) == ("Mary, Jr", 'O"Brien')
    assert first.values["job_role"] == "Line\r\nbreak"
    assert second.row == 3  # Excel shows a multi-line cell in one row


def test_empty_cells_and_absent_optional_columns_are_none() -> None:
    content = _csv(
        HEADER + ",bonus_target",
        "ACME-010001,A,B,a@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,52000,  ",
    )

    [row] = parse_csv(content, max_rows=10)

    assert (row.values["bonus_target"], row.values["currency"]) == (None, None)


def test_values_keep_their_spaces_for_the_validator_to_trim() -> None:
    content = _csv(HEADER, " ACME-010001 ,A,B,a@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,52000")

    [row] = parse_csv(content, max_rows=10)

    assert row.values["employee_code"] == " ACME-010001 "


ROW = "ACME-010001,A,B,a@acme.example,QA,L2,FULL_TIME,DE,2022-04-01,52000"


def test_a_file_that_is_not_utf8_is_refused_with_an_excel_hint() -> None:
    content = (HEADER + "\r\nACME-010001,J\xfcrgen,M\xfcller").encode("cp1252")

    with pytest.raises(UnreadableFile, match="CSV UTF-8"):
        parse_csv(content, max_rows=10)


@pytest.mark.parametrize(
    ("header", "problem"),
    [
        (HEADER.replace("email", "emial"), "Unknown column: emial"),
        (HEADER.replace(",hire_date", ""), "Missing required column: hire_date"),
        (HEADER + ",EMAIL", "email appears more than once"),
        (HEADER.replace(",", ";"), "commas, not semicolons"),
    ],
)
def test_a_header_row_that_does_not_match_the_template_is_refused(
    header: str, problem: str
) -> None:
    with pytest.raises(HeaderMismatch, match=problem):
        parse_csv(_csv(header, ROW), max_rows=10)


def test_a_value_outside_the_header_columns_is_refused_with_its_row() -> None:
    content = _csv(HEADER, ROW, ROW.replace("A,B", "Smith, Jr,B"))

    with pytest.raises(UnreadableFile, match="Row 3 has a value in column K, which has no header"):
        parse_csv(content, max_rows=10)


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (b"", "The file is empty"),
        (_csv(HEADER), "no employee rows"),
        (_csv(HEADER, "", ",,,"), "no employee rows"),
    ],
)
def test_a_file_without_employee_rows_is_refused(content: bytes, problem: str) -> None:
    with pytest.raises(UnreadableFile, match=problem):
        parse_csv(content, max_rows=10)


def test_broken_quoting_is_refused_with_its_row() -> None:
    content = _csv(HEADER, ROW, 'ACME-010002,"A"B,C')

    with pytest.raises(UnreadableFile, match="Row 3"):
        parse_csv(content, max_rows=10)


def test_more_rows_than_the_cap_are_refused_but_blank_rows_do_not_count() -> None:
    assert len(parse_csv(_csv(HEADER, ROW, "", ROW), max_rows=2)) == 2

    with pytest.raises(TooManyRows) as raised:
        parse_csv(_csv(HEADER, ROW, ROW, ROW), max_rows=2)

    assert raised.value.limit == 2


def test_a_header_with_more_than_50_columns_is_refused_at_once() -> None:
    header = ",".join(f"extra_{n}" for n in range(100_000))  # was quadratic: ~110 s

    with pytest.raises(HeaderMismatch, match="at most 50 columns"):
        parse_csv(_csv(header, ROW), max_rows=10)


def test_many_blank_lines_are_refused_as_too_many_rows_without_reading_them_all() -> None:
    content = _csv(HEADER, ROW) + b"\r\n" * 2_000_000

    with pytest.raises(TooManyRows):
        parse_csv(content, max_rows=10)
