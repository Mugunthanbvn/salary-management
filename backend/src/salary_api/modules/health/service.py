import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from salary_api import __version__
from salary_api.core.errors import ServiceUnavailable
from salary_api.modules.health import repository
from salary_api.modules.health.schemas import HealthResponse

_logger = structlog.get_logger(__name__)


def check_health(session: Session) -> HealthResponse:
    try:
        repository.ping(session)
    except SQLAlchemyError as exc:
        _logger.error("health_db_unreachable", error_type=type(exc).__name__)
        raise ServiceUnavailable("The database is not reachable.", db="error") from exc
    return HealthResponse(status="ok", db="ok", version=__version__)
