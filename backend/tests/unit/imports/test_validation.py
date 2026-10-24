"""The validator turns raw rows into import rows or row errors (docs/11 sections 4, 5.2-5.4).

Pure: reference data comes in as a value, so these tests need no database.
"""

from datetime import date
from pathlib import Path

import pytest

from salary_api.domain.enums import ComponentType, EmploymentType, Level
from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.imports.parsing import RawRow, parse_csv, parse_xlsx
from salary_api.modules.imports.validation import (
    ImportReference,
    ImportRow,
    KnownCountry,
    KnownJobRole,
    RowError,
    RowErrorCode,
    mark_db_duplicates,
    validate_rows,
)
from salary_api.modules.salaries.schemas import ComponentIn

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
ENGINEER = KnownJobRole(id=7, title="Software Engineer", department="Engineering")
CSM = KnownJobRole(id=9, title="Customer Success Manager", department="Customer Success")
REFERENCE = ImportReference(
    countries={
        "DE": KnownCountry(code="DE", name="Germany", currency="EUR", is_active=True),
        "IN": KnownCountry(code="IN", name="India", currency="INR", is_active=True),
        "JP": KnownCountry(code="JP", name="Japan", currency="JPY", is_active=True),
        "GB": KnownCountry(code="GB", name="United Kingdom", currency="GBP", is_active=False),
    },
    job_roles=[ENGINEER, CSM],
    today=date(2026, 10, 1),
)


def _raw(row: int = 2, **values: str | None) -> RawRow:
    """A valid row for Germany, changed by `values` (None empties a cell)."""
    cells: dict[str, str | None] = {
        "employee_code": "ACME-010001",
        "first_name": "Lena",
        "last_name": "Müller",
        "email": "lena.mueller@acme.example",
        "job_role": "Software Engineer",
        "level": "L2",
        "employment_type": "FULL_TIME",
        "country": "DE",
        "hire_date": "2022-04-01",
        "base_salary": "52000.00",
    }
    cells |= values
    return RawRow(row=row, values={column: cells.get(column) for column in TEMPLATE_COLUMNS})


def _validate(*rows: RawRow) -> tuple[list[ImportRow], list[RowError]]:
    report = validate_rows(rows, REFERENCE)
    return report.rows, report.errors


def test_a_valid_row_becomes_a_normalized_import_row() -> None:
    raw = _raw(
        employee_code=" ACME-010001 ",
        first_name="  Jürgen ",
        email=" Jurgen.Muller@ACME.example ",
        job_role="software ENGINEER",
        level="l3",
        employment_type="part_time",
        country="de",
        currency="eur",
        bonus_target="4160.5",
        allowance_1_name="Transport",
        allowance_1_amount="1200",
        allowance_3_name="Meals",
        allowance_3_amount="300.25",
        salary_effective_date="2022-05-01",
    )

    rows, errors = _validate(raw)

    assert errors == []
    assert rows == [
        ImportRow(
            row=2,
            employee_code="ACME-010001",
            first_name="Jürgen",
            last_name="Müller",
            email="jurgen.muller@acme.example",
            job_role=ENGINEER,
            level=Level.L3,
            employment_type=EmploymentType.PART_TIME,
            country_code="DE",
            currency="EUR",
            hire_date=date(2022, 4, 1),
            salary_effective_date=date(2022, 5, 1),
            base_minor=5_200_000,
            components=(
                ComponentIn(type=ComponentType.ALLOWANCE, name="Transport", amount_minor=120_000),
                ComponentIn(type=ComponentType.ALLOWANCE, name="Meals", amount_minor=30_025),
                ComponentIn(
                    type=ComponentType.BONUS_TARGET, name="Target bonus", amount_minor=416_050
                ),
            ),
        )
    ]
    assert rows[0].total_minor == 5_766_075


def test_the_currency_and_salary_date_default_to_the_country_and_hire_date() -> None:
    [row], _ = _validate(_raw(country="JP", base_salary="6500000.0"))

    assert (row.currency, row.base_minor, row.salary_effective_date) == (
        "JPY",
        6_500_000,
        date(2022, 4, 1),
    )


ROLES = "Customer Success Manager, Software Engineer"


@pytest.mark.parametrize(
    ("cells", "column", "code", "message"),
    [
        ({"employee_code": None}, "employee_code", "required", "employee_code is required"),
        ({"employee_code": "ACME-12"}, "employee_code", "invalid_format", "ACME- and six"),
        ({"first_name": "x" * 101}, "first_name", "invalid_format", "at most 100"),
        ({"last_name": None}, "last_name", "required", "last_name is required"),
        ({"email": "lena-at-acme"}, "email", "invalid_format", "not a valid email"),
        (
            {"job_role": "Sr Engineer"},
            "job_role",
            "unknown_value",
            f"Did you mean 'Software Engineer'? Job roles: {ROLES}.",
        ),
        ({"job_role": "Chef"}, "job_role", "unknown_value", f"Job roles: {ROLES}."),
        ({"level": "L7"}, "level", "unknown_value", "L1, L2, L3, L4, L5, L6"),
        ({"employment_type": "INTERN"}, "employment_type", "unknown_value", "FULL_TIME, PART"),
        ({"country": "XX"}, "country", "unknown_value", "Countries: DE, IN, JP."),
        ({"country": "GB"}, "country", "unknown_value", "Countries: DE, IN, JP."),
        ({"hire_date": "03/04/2022"}, "hire_date", "invalid_format", "YYYY-MM-DD"),
        ({"hire_date": "2022-02-30"}, "hire_date", "invalid_format", "YYYY-MM-DD"),
        ({"hire_date": "2026-10-02"}, "hire_date", "future_date", "cannot be in the future"),
        ({"hire_date": "1969-12-31"}, "hire_date", "invalid_format", "1970-01-01"),
        ({"currency": "USD"}, "currency", "currency_mismatch", "Germany are paid in EUR"),
        ({"base_salary": None}, "base_salary", "required", "base_salary is required"),
        ({"base_salary": "52,000.00"}, "base_salary", "invalid_format", "like 52000.00"),
        ({"base_salary": "€52000"}, "base_salary", "invalid_format", "like 52000.00"),
        ({"base_salary": "1e5"}, "base_salary", "invalid_format", "like 52000.00"),
        ({"base_salary": "0"}, "base_salary", "invalid_format", "more than 0"),
        ({"base_salary": "-5"}, "base_salary", "invalid_format", "more than 0"),
        ({"base_salary": "52000.555"}, "base_salary", "too_many_decimals", "at most 2 decimals"),
        (
            {"country": "JP", "base_salary": "450000.5"},
            "base_salary",
            "too_many_decimals",
            "JPY amounts can't have decimals",
        ),
        ({"bonus_target": "-1"}, "bonus_target", "invalid_format", "cannot be negative"),
        (
            {"allowance_1_name": "Transport"},
            "allowance_1_amount",
            "required",
            "Allowance 1 needs an amount",
        ),
        (
            {"allowance_2_amount": "100"},
            "allowance_2_name",
            "required",
            "Allowance 2 needs a name",
        ),
        (
            {"allowance_1_name": "Meals", "allowance_1_amount": "0"},
            "allowance_1_amount",
            "invalid_format",
            "more than 0",
        ),
        (
            {"allowance_1_name": "x" * 61, "allowance_1_amount": "1"},
            "allowance_1_name",
            "invalid_format",
            "at most 60",
        ),
        (
            {
                "allowance_1_name": "Meals",
                "allowance_1_amount": "1",
                "allowance_2_name": "meals",
                "allowance_2_amount": "2",
            },
            "allowance_2_name",
            "invalid_format",
            "same name as allowance 1",
        ),
        (
            {"salary_effective_date": "2022-03-31"},
            "salary_effective_date",
            "before_hire_date",
            "before the hire date",
        ),
        (
            {"salary_effective_date": "2026-10-02"},
            "salary_effective_date",
            "future_date",
            "cannot be in the future",
        ),
        (
            {"salary_effective_date": "2022/05/01"},
            "salary_effective_date",
            "invalid_format",
            "YYYY-MM-DD",
        ),
    ],
)
def test_each_broken_rule_is_a_row_error_with_its_code(
    cells: dict[str, str | None], column: str, code: str, message: str
) -> None:
    rows, errors = _validate(_raw(row=7, **cells))

    assert rows == []
    assert [(e.row, e.column, e.code) for e in errors] == [(7, column, RowErrorCode(code))]
    assert message in errors[0].message
    assert errors[0].value == (cells[column].strip() if cells.get(column) else None)


def test_every_error_of_every_row_is_reported_in_row_and_column_order() -> None:
    rows, errors = _validate(
        _raw(row=2),
        _raw(row=3, employee_code="ACME-010002", email="b@acme.example", level="L9", country="XX"),
        _raw(row=4, employee_code="bad", email="c@acme.example", base_salary="free"),
    )

    assert [row.row for row in rows] == [2]
    assert [(e.row, e.column) for e in errors] == [
        (3, "level"),
        (3, "country"),
        (4, "employee_code"),
        (4, "base_salary"),
    ]


def test_a_row_with_an_unknown_country_still_reports_a_badly_written_amount() -> None:
    _, errors = _validate(_raw(country="XX", base_salary="52.000,00"))

    assert [(e.column, e.code) for e in errors] == [
        ("country", RowErrorCode.UNKNOWN_VALUE),
        ("base_salary", RowErrorCode.INVALID_FORMAT),
    ]


def test_codes_and_emails_repeated_in_the_file_are_errors_on_the_later_rows() -> None:
    rows, errors = _validate(
        _raw(row=2),
        _raw(row=3, email="other@acme.example"),
        _raw(row=4, employee_code="ACME-010004", email="LENA.MUELLER@acme.example"),
    )

    assert [row.row for row in rows] == [2]
    assert [(e.row, e.column, e.code, e.message) for e in errors] == [
        (3, "employee_code", RowErrorCode.DUPLICATE_IN_FILE, "Same employee_code as row 2."),
        (4, "email", RowErrorCode.DUPLICATE_IN_FILE, "Same email as row 2."),
    ]


def test_codes_and_emails_already_in_the_database_are_errors_on_their_rows() -> None:
    report = validate_rows(
        [_raw(row=2), _raw(row=3, employee_code="ACME-010002", email="b@acme.example")],
        REFERENCE,
    )

    checked = mark_db_duplicates(
        report, taken_codes={"ACME-010001"}, taken_emails={"b@acme.example": "ACME-000042"}
    )

    assert checked.rows == []
    assert [(e.row, e.column, e.code, e.message) for e in checked.errors] == [
        (
            2,
            "employee_code",
            RowErrorCode.DUPLICATE_IN_DB,
            "ACME-010001 is already used by an employee.",
        ),
        (3, "email", RowErrorCode.DUPLICATE_IN_DB, "This email is already used by ACME-000042."),
    ]
    assert checked.row_count == 2


def test_the_csv_and_xlsx_golden_files_give_identical_reports() -> None:
    csv_rows = parse_csv((FIXTURES / "import_sample.csv").read_bytes(), max_rows=10)
    xlsx_rows = parse_xlsx(
        (FIXTURES / "import_sample.xlsx").read_bytes(), max_rows=10, max_uncompressed_bytes=10**8
    )

    from_csv = validate_rows(csv_rows, REFERENCE)
    from_xlsx = validate_rows(xlsx_rows, REFERENCE)

    assert from_xlsx == from_csv
    assert [row.row for row in from_csv.rows] == [2, 3, 4]
    assert [(e.row, e.column, e.code) for e in from_csv.errors] == [
        (5, "job_role", RowErrorCode.UNKNOWN_VALUE),
        (5, "base_salary", RowErrorCode.TOO_MANY_DECIMALS),
    ]
