"""Refuse a request whose declared body is over the upload cap, before it is read.

Starlette parses (and spools to a temporary file) a multipart body before any route code
runs, so the cap is checked here on `Content-Length`. A body sent without one (chunked) is
still capped by the import service after reading (docs/08-security-rbac.md section 7.2).
"""

from typing import Final

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from salary_api.core.errors import PayloadTooLarge, problem_response
from salary_api.domain.constants import MAX_UPLOAD_BYTES

MULTIPART_OVERHEAD: Final = 64 * 1024
"""Room for the multipart boundaries and part headers around a 4 MB file."""
MAX_BODY_BYTES: Final = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD


class BodySizeLimitMiddleware:
    """Pure ASGI middleware: 413 problem+json for a declared body over MAX_BODY_BYTES."""

    def __init__(self, app: ASGIApp, *, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._declared_size(scope) > self.max_bytes:
            megabytes = MAX_UPLOAD_BYTES // (1024 * 1024)
            problem = PayloadTooLarge(f"Upload at most {megabytes} MB.")
            await problem_response(Request(scope), problem)(scope, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _declared_size(scope: Scope) -> int:
        for name, value in scope["headers"]:
            if name == b"content-length":
                return int(value) if value.isdigit() else 0
        return 0
