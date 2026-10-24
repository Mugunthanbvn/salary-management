from fastapi import APIRouter, Depends

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission
from salary_api.modules.reference import service
from salary_api.modules.reference.schemas import Country, ReferenceData

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
