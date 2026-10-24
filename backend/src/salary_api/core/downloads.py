"""File downloads (CSV and XLSX): what services return, and how routers send it."""

from dataclasses import dataclass
from typing import Any, Final

from fastapi import Response

from salary_api.core.schemas import FileFormat

CSV_MEDIA_TYPE: Final = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE: Final = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MEDIA_TYPES: Final = {FileFormat.CSV: CSV_MEDIA_TYPE, FileFormat.XLSX: XLSX_MEDIA_TYPE}

# OpenAPI for a route that answers 200 with a CSV or an XLSX file.
FILE_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    200: {
        "description": "The file, as an attachment",
        "content": {
            media_type: {"schema": {"type": "string", "format": "binary"}}
            for media_type in MEDIA_TYPES.values()
        },
    }
}


@dataclass(frozen=True, slots=True)
class DownloadFile:
    content: bytes
    media_type: str
    filename: str  # built by the service, never taken from the request


def file_response(download: DownloadFile) -> Response:
    """The file as an attachment the browser saves under `download.filename`."""
    return Response(
        content=download.content,
        media_type=download.media_type,
        headers={"Content-Disposition": f'attachment; filename="{download.filename}"'},
    )
