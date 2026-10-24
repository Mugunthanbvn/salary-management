"""RFC 9457 problem+json error responses (docs/07-api-spec.md section 1.5).

`type` is `https://acme.example/problems/<slug>` with a slug from docs/glossary.md section 5.
A status with no glossary slug uses `about:blank` and the HTTP status phrase as the title.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, TypedDict

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from salary_api.core.request_id import REQUEST_ID_HEADER

PROBLEM_JSON = "application/problem+json"
PROBLEM_TYPE_BASE = "https://acme.example/problems/"

_logger = structlog.get_logger(__name__)

# Statuses whose meaning is a single glossary slug, for errors raised by the framework.
_SLUG_AND_TITLE_FOR_STATUS: dict[int, tuple[str, str]] = {
    400: ("bad-request", "Bad request"),
    401: ("unauthenticated", "Not authenticated"),
    403: ("forbidden", "Forbidden"),
    404: ("not-found", "Not found"),
    413: ("payload-too-large", "Payload too large"),
    415: ("unsupported-media-type", "Unsupported media type"),
    429: ("rate-limited", "Too many requests"),
}


class ProblemError(Exception):
    """An error that becomes a problem+json response. `slug=None` means `about:blank`."""

    def __init__(
        self, status: int, slug: str | None, title: str, detail: str | None = None, **extra: Any
    ) -> None:
        super().__init__(detail or title)
        self.status = status
        self.slug = slug
        self.title = title
        self.detail = detail
        self.extra = extra


class FieldError(TypedDict):
    loc: list[str | int]
    code: str
    message: str


class ValidationFailed(ProblemError):
    """422: field-level errors in a JSON body or query, listed in `errors[]`."""

    def __init__(self, errors: list[FieldError], detail: str | None = None) -> None:
        count = "1 field is" if len(errors) == 1 else f"{len(errors)} fields are"
        super().__init__(
            422, "validation", "Validation failed", detail or f"{count} invalid.", errors=errors
        )


def problem_response(
    request: Request, problem: ProblemError, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}{problem.slug}" if problem.slug else "about:blank",
        "title": problem.title,
        "status": problem.status,
    }
    if problem.detail is not None:
        body["detail"] = problem.detail
    request_id: str | None = getattr(request.state, "request_id", None)
    body["instance"] = request.url.path
    body["request_id"] = request_id
    body.update(problem.extra)
    # Set here too, because a 500 is sent from outside the request id middleware.
    response_headers = {
        **(headers or {}),
        **({REQUEST_ID_HEADER: request_id} if request_id else {}),
    }
    return JSONResponse(
        body, status_code=problem.status, media_type=PROBLEM_JSON, headers=response_headers
    )


def _from_http_exception(exc: StarletteHTTPException) -> ProblemError:
    phrase = HTTPStatus(exc.status_code).phrase
    slug, title = _SLUG_AND_TITLE_FOR_STATUS.get(exc.status_code, (None, phrase))
    detail = exc.detail if exc.detail != phrase else None
    return ProblemError(exc.status_code, slug, title, detail)


def _from_request_validation_error(exc: RequestValidationError) -> ValidationFailed:
    errors: list[FieldError] = [
        {"loc": list(error["loc"]), "code": error["type"], "message": error["msg"]}
        for error in exc.errors()
    ]
    return ValidationFailed(errors)


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem_response(request, _from_http_exception(exc), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(request, _from_request_validation_error(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        _logger.error("unhandled_error", path=request.url.path, exc_info=exc)
        problem = ProblemError(500, None, "Internal Server Error", "An unexpected error occurred.")
        return problem_response(request, problem)
