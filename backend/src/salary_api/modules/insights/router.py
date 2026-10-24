from typing import Annotated

from fastapi import APIRouter, Depends, Query

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import (
    ByDepartment,
    ByJobTitle,
    CohortMembers,
    CohortQuery,
    DepartmentCosts,
    InsightQuery,
    JobTitleQuery,
    Overview,
    PayEquity,
    PayEquityCohorts,
    PayEquityDepartments,
    PayEquityQuery,
    TopEarners,
    TopEarnersQuery,
)

router = APIRouter(prefix="/insights", tags=["insights"])

CanReadInsights = Annotated[Principal, Depends(require_permission(Permission.INSIGHTS_READ))]
CanReadIndividuals = Annotated[
    Principal, Depends(require_permission(Permission.INSIGHTS_READ, Permission.SALARY_READ))
]


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


@router.get(
    "/department-cost",
    response_model=DepartmentCosts,
    responses=problem_responses(401, 403),
    summary="Total pay per department and its share of the total",
)
def department_cost(
    query: Annotated[InsightQuery, Query()], principal: CanReadInsights, session: SessionDep
) -> DepartmentCosts:
    return service.department_cost(session, principal, query)


@router.get(
    "/top-earners",
    response_model=TopEarners,
    responses=problem_responses(401, 403),
    summary="Highest or lowest paid people in one country (SALARY_READ; audited)",
)
def top_earners(
    query: Annotated[TopEarnersQuery, Query()], principal: CanReadIndividuals, session: SessionDep
) -> TopEarners:
    return service.top_earners(session, principal, query)


@router.get(
    "/pay-equity",
    response_model=PayEquity,
    responses=problem_responses(401, 403),
    summary="Compa-ratios against pay bands, per cohort or per department of one country",
)
def pay_equity(
    query: Annotated[PayEquityQuery, Query()], principal: CanReadInsights, session: SessionDep
) -> PayEquityCohorts | PayEquityDepartments:
    return service.pay_equity(session, principal, query)


@router.get(
    "/pay-equity/cohort",
    response_model=CohortMembers,
    responses=problem_responses(401, 403),
    summary="One cohort's members against their band (SALARY_READ; audited)",
)
def pay_equity_cohort(
    query: Annotated[CohortQuery, Query()], principal: CanReadIndividuals, session: SessionDep
) -> CohortMembers:
    return service.pay_equity_cohort(session, principal, query)
