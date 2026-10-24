"""The import template: the header row and one example row (docs/11-import-export.md section 4).

The XLSX template also has a protected "Reference" sheet with the valid job roles, levels,
employment types, countries and currencies, and dropdowns on those columns that list them.
Pure: the reference data comes in as values.
"""

import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from salary_api.domain.constants import MAX_IMPORT_ROWS
from salary_api.domain.enums import EmploymentType, Level
from salary_api.domain.money import Money
from salary_api.modules.exports.writers import CellValue, csv_bytes
from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.imports.validation import KnownCountry, KnownJobRole

EXAMPLE_ROLE = "Software Engineer"
EXAMPLE_COUNTRY = "DE"
EXAMPLE_DATE = date(2022, 4, 1)
REFERENCE_SHEET = "Reference"
REFERENCE_COLUMNS = (
    "job_role",
    "department",
    "level",
    "level_name",
    "employment_type",
    "country",
    "country_name",
    "currency",
)
# Template columns with a dropdown of the Reference column of the same name.
DROPDOWNS = ("job_role", "level", "employment_type", "country", "currency")


@dataclass(frozen=True, slots=True)
class TemplateReference:
    job_roles: Sequence[KnownJobRole]  # by title
    countries: Sequence[KnownCountry]  # the active ones, by code


def csv_template(reference: TemplateReference) -> bytes:
    return csv_bytes(TEMPLATE_COLUMNS, [_example(reference, as_text=True)])


def xlsx_template(reference: TemplateReference) -> bytes:
    # Imported here, not at the top: openpyxl is slow to import (docs/19 section 6.3).
    from openpyxl import Workbook  # noqa: PLC0415
    from openpyxl.worksheet.datavalidation import DataValidation  # noqa: PLC0415

    workbook = Workbook()
    employees = workbook.worksheets[0]
    employees.title = "Employees"
    employees.append(list(TEMPLATE_COLUMNS))
    employees.append(_example(reference, as_text=False))
    for cell in employees[2]:
        if isinstance(cell.value, date):
            cell.number_format = "yyyy-mm-dd"
    lists = _reference_lists(reference)
    sheet = workbook.create_sheet(REFERENCE_SHEET)
    sheet.append(list(REFERENCE_COLUMNS))
    longest = max(len(values) for values in lists.values())
    for index in range(longest):
        sheet.append([_at(lists[column], index) for column in REFERENCE_COLUMNS])
    sheet.protection.sheet = True  # read-only, to stop accidental edits
    for column in DROPDOWNS:
        letter = _letter(TEMPLATE_COLUMNS.index(column))
        source = _letter(REFERENCE_COLUMNS.index(column))
        last = max(1, len(lists[column])) + 1
        validation = DataValidation(
            type="list",
            formula1=f"{REFERENCE_SHEET}!${source}$2:${source}${last}",
            sqref=f"{letter}2:{letter}{MAX_IMPORT_ROWS + 1}",
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Not a valid value",
            error=f"Choose a {column} from the {REFERENCE_SHEET} sheet.",
        )
        employees.add_data_validation(validation)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _example(reference: TemplateReference, *, as_text: bool) -> list[CellValue]:
    """One row that imports as is: a role and a country of the reference data."""
    titles = [role.title for role in reference.job_roles]
    role = EXAMPLE_ROLE if EXAMPLE_ROLE in titles else next(iter(titles), None)
    codes = {country.code: country for country in reference.countries}
    country = codes.get(EXAMPLE_COUNTRY) or next(iter(reference.countries), None)
    currency = country.currency if country else None

    def amount(major: str) -> CellValue:
        if currency is None:
            return None
        value = Money.from_major(major, currency).to_major()  # 52000.00 EUR, 52000 JPY
        return str(value) if as_text else value

    day: CellValue = EXAMPLE_DATE.isoformat() if as_text else EXAMPLE_DATE
    cells: dict[str, CellValue] = {
        "employee_code": "ACME-010001",
        "first_name": "Jürgen",
        "last_name": "Müller",
        "email": "jurgen.muller@acme.example",
        "job_role": role,
        "level": Level.L2.value,
        "employment_type": EmploymentType.FULL_TIME.value,
        "country": country.code if country else None,
        "hire_date": day,
        "currency": currency,
        "base_salary": amount("52000"),
        "bonus_target": amount("4160"),
        "allowance_1_name": "Transport",
        "allowance_1_amount": amount("1200"),
        "salary_effective_date": day,
    }
    return [cells.get(column) for column in TEMPLATE_COLUMNS]


def _reference_lists(reference: TemplateReference) -> dict[str, list[str]]:
    return {
        "job_role": [role.title for role in reference.job_roles],
        "department": [role.department for role in reference.job_roles],
        "level": [level.value for level in Level],
        "level_name": [level.label for level in Level],
        "employment_type": [kind.value for kind in EmploymentType],
        "country": [country.code for country in reference.countries],
        "country_name": [country.name for country in reference.countries],
        "currency": sorted({country.currency for country in reference.countries}),
    }


def _at(values: Sequence[str], index: int) -> str | None:
    return values[index] if index < len(values) else None


def _letter(position: int) -> str:
    """The column letter of a 0-based position (the template has fewer than 26 columns)."""
    return chr(ord("A") + position)
