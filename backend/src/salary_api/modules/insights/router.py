from typing import Annotated

from fastapi import APIRouter, Depends, Query

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import InsightQuery, Overview

router = APIRouter(prefix="/insights", tags=["insights"])

CanReadInsights = Annotated[Principal, Depends(require_permission(Permission.INSIGHTS_READ))]


@router.get(
    "/overview",
    response_model=Overview,
    responses=problem_responses(401, 403),
    summary="Headcount, payroll and pay by country",
)
def overview(
    query: Annotated[InsightQuery, Query()], principal: CanReadInsights, session: SessionDep
) -> Overview:
    return service.overview(session, principal, query)
