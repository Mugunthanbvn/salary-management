"""RFC 9457 problem+json error responses (docs/07-api-spec.md section 1.5).

`type` is `https://acme.example/problems/<slug>` with a slug from docs/glossary.md section 5.
A status with no glossary slug uses `about:blank` and the HTTP status phrase as the title.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, TypedDict

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
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
        self.headers: dict[str, str] = {}


class Unauthenticated(ProblemError):
    """401: missing, invalid or expired token, or an inactive user."""

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(401, "unauthenticated", "Not authenticated", detail, **extra)


class Forbidden(ProblemError):
    """403: the caller lacks the required permission."""

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(403, "forbidden", "Forbidden", detail, **extra)


class NotFound(ProblemError):
    """404: unknown resource, or one the caller may not see."""

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(404, "not-found", "Not found", detail, **extra)


class VersionConflict(ProblemError):
    """409: optimistic lock failure; the body carries `current_version`."""

    def __init__(self, detail: str, *, current_version: int) -> None:
        super().__init__(
            409, "version-conflict", "Version conflict", detail, current_version=current_version
        )


class Duplicate(ProblemError):
    """409: a unique value (employee_code, email) is already taken."""

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(409, "duplicate", "Duplicate", detail, **extra)


class InvalidState(ProblemError):
    """409: the resource is in the wrong state for this action."""

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(409, "invalid-state", "Invalid state", detail, **extra)


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


class RateLimited(ProblemError):
    """429: too many attempts. Always sends `Retry-After` (seconds)."""

    def __init__(self, detail: str, *, retry_after_seconds: int) -> None:
        super().__init__(429, "rate-limited", "Too many requests", detail)
        self.headers["Retry-After"] = str(retry_after_seconds)


class ServiceUnavailable(ProblemError):
    """503 with no glossary slug (`about:blank`): a dependency such as the database is down."""

    def __init__(self, detail: str, **extra: Any) -> None:
        super().__init__(503, None, "Service Unavailable", detail, **extra)


class Problem(BaseModel):
    """An RFC 9457 problem. Some problems add members, e.g. `current_version`."""

    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str
    request_id: str | None = None


class ValidationProblem(Problem):
    """422 `validation`: one entry in `errors` per invalid field."""

    errors: list[FieldError]


# App-wide error responses for the OpenAPI document. Declaring 422 also replaces FastAPI's
# default HTTPValidationError schema, which is not what the API sends.
PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ValidationProblem, "description": "Validation failed"},
    "4XX": {"model": Problem, "description": "Client error"},
    "5XX": {"model": Problem, "description": "Server error"},
}


# Route-level error responses, more specific than the app-wide 4XX.
_ROUTE_PROBLEMS: dict[int, dict[str, Any]] = {
    401: {
        "model": Problem,
        "description": "Not authenticated: no valid session, or the user is inactive",
    },
    403: {"model": Problem, "description": "Forbidden: a required permission is missing"},
    429: {
        "model": Problem,
        "description": "Too many requests",
        "headers": {
            "Retry-After": {
                "description": "Seconds to wait before trying again",
                "schema": {"type": "integer"},
            }
        },
    },
}


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` for the problems a route can send: `problem_responses(401, 403)`."""
    return {status: _ROUTE_PROBLEMS[status] for status in statuses}


def use_problem_json_in_openapi(app: FastAPI) -> None:
    """Document error responses as application/problem+json, the media type they are sent as.

    FastAPI files every response model under the route's own media type (application/json).
    """
    build_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            for path_item in build_openapi()["paths"].values():
                for operation in path_item.values():
                    for status, response in operation["responses"].items():
                        content = response.get("content", {})
                        if status[0] in "45" and "application/json" in content:
                            content[PROBLEM_JSON] = content.pop("application/json")
        return app.openapi_schema or {}

    app.openapi = openapi


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
    response_headers = dict(headers or {})
    if request_id:
        # Set here too, because a 500 is sent from outside the request id middleware.
        response_headers[REQUEST_ID_HEADER] = request_id
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
    @app.exception_handler(ProblemError)
    async def handle_problem_error(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(request, exc, exc.headers)

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
        if isinstance(exc, ResponseValidationError):
            # Its message holds the response body (salary data): log the type only.
            _logger.error("unhandled_error", path=request.url.path, error_type=type(exc).__name__)
        else:
            _logger.error("unhandled_error", path=request.url.path, exc_info=exc)
        problem = ProblemError(500, None, "Internal Server Error", "An unexpected error occurred.")
        return problem_response(request, problem)
