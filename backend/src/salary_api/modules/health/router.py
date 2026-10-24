from fastapi import APIRouter

from salary_api.core.deps import SessionDep
from salary_api.modules.health import service
from salary_api.modules.health.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Health check (public)")
def health(session: SessionDep) -> HealthResponse:
    return service.check_health(session)
