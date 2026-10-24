"""Build CSV and XLSX upload files in tests."""

import io
import zipfile
from collections.abc import Sequence

from openpyxl import Workbook

from salary_api.modules.imports.columns import TEMPLATE_COLUMNS

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
