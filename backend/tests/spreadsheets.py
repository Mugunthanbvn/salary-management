"""Build CSV and XLSX upload files in tests."""

import io
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any

from openpyxl import Workbook
from sqlalchemy.orm import Session

from salary_api.modules.imports.columns import TEMPLATE_COLUMNS
from salary_api.modules.reference.models import JobRole
from tests.factories import make_country, make_job_role

FULL_HEADER = list(TEMPLATE_COLUMNS)


def xlsx_bytes(
    rows: Sequence[Sequence[object]],
    *,
    title: str = "Employees",
    sheets_before: Sequence[str] = (),
) -> bytes:
    """A workbook whose sheet `title` holds `rows` (typed cells), after empty `sheets_before`."""
    workbook = Workbook()
    first = workbook.active
    assert first is not None
    workbook.remove(first)
    for name in sheets_before:
        workbook.create_sheet(name).append(["Not the employees"])
    sheet = workbook.create_sheet(title)
    for row in rows:
        sheet.append(list(row))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def replace_in_sheets(content: bytes, old: str, new: str) -> bytes:
    """The workbook with `old` replaced by `new` in each worksheet's XML (to fake what Excel
    writes, such as a formula's saved value)."""
    source = zipfile.ZipFile(io.BytesIO(content))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item)
            if item.filename.startswith("xl/worksheets/"):
                data = data.replace(old.encode(), new.encode())
            target.writestr(item, data)
    return buffer.getvalue()


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def csv_bytes(rows: Sequence[Sequence[object]], *, bom: bool = True) -> bytes:
    """A UTF-8 CSV (with a BOM, as Excel writes it); None is an empty cell. No quoting:
    keep commas out of the values."""
    lines = [",".join("" if cell is None else str(cell) for cell in row) for row in rows]
    return ("﻿" if bom else "").encode() + ("\r\n".join(lines) + "\r\n").encode()


def hire(number: int = 1, **cells: object) -> dict[str, object]:
    """The cells of one valid import row: a Software Engineer hired in Germany in 2022."""
    row: dict[str, object] = {
        "employee_code": f"ACME-{10_000 + number:06d}",
        "first_name": "Lena",
        "last_name": f"Müller {number}",
        "email": f"lena.{number}@acme.example",
        "job_role": "Software Engineer",
        "level": "L2",
        "employment_type": "FULL_TIME",
        "country": "DE",
        "hire_date": "2022-04-01",
        "base_salary": "52000.00",
    }
    return row | cells


def import_csv(*rows: Mapping[str, object]) -> bytes:
    """A CSV of the full template with these rows."""
    return csv_bytes([FULL_HEADER, *([row.get(column) for column in FULL_HEADER] for row in rows)])


def import_xlsx(*rows: Mapping[str, object]) -> bytes:
    """An XLSX of the full template with these rows (cells as given, so text by default)."""
    return xlsx_bytes([FULL_HEADER, *([row.get(column) for column in FULL_HEADER] for row in rows)])


CSV_TYPE = "text/csv"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def upload(filename: str, content: bytes, content_type: str = CSV_TYPE) -> dict[str, Any]:
    """TestClient keyword arguments that post `content` as the multipart field `file`."""
    return {"files": {"file": (filename, content, content_type)}}


def make_import_reference(session: Session) -> JobRole:
    """Countries DE, JP and IN, and the Software Engineer role (returned) to import into."""
    for code in ("DE", "JP", "IN"):
        make_country(session, code)
    return make_job_role(session, "Software Engineer")
