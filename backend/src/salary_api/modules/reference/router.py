from typing import Annotated

from fastapi import APIRouter, Depends, Query

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission
from salary_api.modules.reference import service
from salary_api.modules.reference.schemas import (
    Country,
    FxRates,
    PayBandQuery,
    PayBands,
    ReferenceData,
)

router = APIRouter(
    tags=["reference"], dependencies=[Depends(require_permission(Permission.EMPLOYEE_READ))]
)


@router.get(
    "/reference",
    response_model=ReferenceData,
    responses=problem_responses(401, 403),
    summary="Reference data for forms and filters",
)
def reference(session: SessionDep) -> ReferenceData:
    return service.reference_data(session)


@router.get(
    "/countries",
    response_model=list[Country],
    responses=problem_responses(401, 403),
    summary="Countries and their salary currency",
)
def countries(session: SessionDep) -> list[Country]:
    return service.countries(session)


# Pay bands and FX rates are what insights are measured against, so they need INSIGHTS_READ.
insights_router = APIRouter(
    tags=["reference"], dependencies=[Depends(require_permission(Permission.INSIGHTS_READ))]
)


@insights_router.get(
    "/pay-bands",
    response_model=PayBands,
    responses=problem_responses(401, 403),
    summary="Pay bands in force today (read-only)",
)
def pay_bands(query: Annotated[PayBandQuery, Query()], session: SessionDep) -> PayBands:
    return service.pay_bands(session, query)


@insights_router.get(
    "/fx-rates",
    response_model=FxRates,
    responses=problem_responses(401, 403),
    summary="Current USD rates with their date and source",
)
def fx_rates(session: SessionDep) -> FxRates:
    return service.fx_rates(session)
