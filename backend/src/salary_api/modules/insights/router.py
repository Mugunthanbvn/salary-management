from typing import Annotated

from fastapi import APIRouter, Depends, Query

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import (
    ByDepartment,
    ByJobTitle,
    InsightQuery,
    JobTitleQuery,
    Overview,
)

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


@router.get(
    "/by-department",
    response_model=ByDepartment,
    responses=problem_responses(401, 403),
    summary="Pay statistics per department",
)
def by_department(
    query: Annotated[InsightQuery, Query()], principal: CanReadInsights, session: SessionDep
) -> ByDepartment:
    return service.by_department(session, principal, query)


@router.get(
    "/by-job-title",
    response_model=ByJobTitle,
    responses=problem_responses(401, 403),
    summary="Pay statistics per job title within one country",
)
def by_job_title(
    query: Annotated[JobTitleQuery, Query()], principal: CanReadInsights, session: SessionDep
) -> ByJobTitle:
    return service.by_job_title(session, principal, query)
