"""structlog JSON logging: one JSON object per line on stdout.

Context such as `request_id` is merged into every line (see core/request_id.py).
Never log request or response bodies, secrets, tokens, passwords or salary rows.
"""

import logging

import structlog
from structlog.tracebacks import ExceptionDictTransformer

from salary_api.core.config import LogLevel


def configure_logging(level: LogLevel) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Tracebacks without frame locals: locals can hold secrets or salary values.
            structlog.processors.ExceptionRenderer(ExceptionDictTransformer(show_locals=False)),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
