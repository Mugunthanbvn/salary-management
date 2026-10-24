from typing import Annotated

from fastapi import APIRouter, Depends

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.salaries import service
from salary_api.modules.salaries.schemas import SalaryChange, SalaryChangeRequest

router = APIRouter(prefix="/employees", tags=["salaries"])

CanChangeSalary = Annotated[Principal, Depends(require_permission(Permission.SALARY_WRITE))]


@router.post(
    "/{employee_id:int}/salary-changes",
    status_code=201,
    response_model=SalaryChange,
    responses=problem_responses(401, 403, 404, 409),
    summary="Record a salary change (appends to the history)",
)
def record_salary_change(
    employee_id: int, body: SalaryChangeRequest, principal: CanChangeSalary, session: SessionDep
) -> SalaryChange:
    return service.record_salary_change(session, principal, employee_id, body)
