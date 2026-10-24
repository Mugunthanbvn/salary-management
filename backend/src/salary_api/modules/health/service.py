from sqlalchemy.orm import Session

from salary_api import __version__
from salary_api.modules.health import repository
from salary_api.modules.health.schemas import HealthResponse


def check_health(session: Session) -> HealthResponse:
    repository.ping(session)
    return HealthResponse(status="ok", db="ok", version=__version__)
