from typing import Annotated

from fastapi import APIRouter, Depends

from salary_api.core.deps import IdPath, SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.salaries import service
from salary_api.modules.salaries.schemas import SalaryChange, SalaryChangeRequest, SalaryHistory

router = APIRouter(prefix="/employees", tags=["salaries"])

CanReadSalary = Annotated[Principal, Depends(require_permission(Permission.SALARY_READ))]
CanChangeSalary = Annotated[Principal, Depends(require_permission(Permission.SALARY_WRITE))]


@router.post(
    "/{employee_id:int}/salary-changes",
    status_code=201,
    response_model=SalaryChange,
    responses=problem_responses(401, 403, 404, 409),
    summary="Record a salary change (appends to the history)",
)
def record_salary_change(
    employee_id: IdPath, body: SalaryChangeRequest, principal: CanChangeSalary, session: SessionDep
) -> SalaryChange:
    return service.record_salary_change(session, principal, employee_id, body)


@router.get(
    "/{employee_id:int}/salary-history",
    response_model=SalaryHistory,
    responses=problem_responses(401, 403, 404),
    summary="Salary history, oldest first (SALARY_READ only)",
)
def salary_history(
    employee_id: IdPath, principal: CanReadSalary, session: SessionDep
) -> SalaryHistory:
    return service.salary_history(session, principal, employee_id)
