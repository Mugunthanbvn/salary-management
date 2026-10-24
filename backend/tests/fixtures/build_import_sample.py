"""Write tests/fixtures/import_sample.xlsx: the rows of import_sample.csv as an Excel user has them.

Numbers are number cells, dates are date cells, empty cells are left out, and the header
row has other spelling and order, so the golden test checks what the XLSX parser undoes.

Run from backend/: `uv run python -m tests.fixtures.build_import_sample`.
"""

from datetime import date
from pathlib import Path

from openpyxl import Workbook

FIXTURES = Path(__file__).resolve().parent

# The same employees as import_sample.csv, with typed cells.
HEADER = [
    " Employee_Code ",
    "FIRST_NAME",
    "last_name",
    "Email",
    "job_role",
    "Level",
    "employment_type",
    "Country",
    "hire_date",
    "currency",
    "base_salary",
    "bonus_target",
    "allowance_1_name",
    "allowance_1_amount",
    "allowance_2_name",
    "allowance_2_amount",
    "allowance_3_name",
    "allowance_3_amount",
    "salary_effective_date",
]
ROWS: list[list[object]] = [
    [
        "ACME-010001",
        "Jürgen",
        "Müller",
        "Jurgen.Muller@acme.example",
        "Software Engineer",
        "L2",
        "FULL_TIME",
        "DE",
        date(2022, 4, 1),
        "EUR",
        52000,
        4160.5,
        "Transport",
        1200,
        None,
        None,
        None,
        None,
        date(2022, 4, 1),
    ],
    [
        "ACME-010002",
        "花子",
        "佐藤",
        "hanako.sato@acme.example",
        "software engineer",
        "l3",
        "full_time",
        "jp",
        date(2021, 7, 15),
        None,
        6500000,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ],
    [
        "ACME-010003",
        "Ananya",
        "Rao",
        "a.rao@acme.example",
        "Customer Success Manager",
        "L1",
        "PART_TIME",
        "IN",
        date(2023, 1, 9),
        "INR",
        1500000,
        None,
        "HRA",
        600000,
        "Special allowance",
        120000.75,
        None,
        None,
        date(2023, 2, 1),
    ],
    [
        "ACME-010004",
        "José",
        "García",
        "jose.garcia@acme.example",
        "Sr Engineer",
        "L2",
        "CONTRACTOR",
        "JP",
        date(2024, 5, 20),
        "JPY",
        450000.5,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ],
]


def build(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Employees"
    sheet.append(HEADER)
    for row in ROWS:
        sheet.append(row)
    workbook.save(path)


if __name__ == "__main__":
    build(FIXTURES / "import_sample.xlsx")
