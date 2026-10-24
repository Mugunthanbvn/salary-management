from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.employees import service
from salary_api.modules.employees.schemas import EmployeeCreate, EmployeeDetail

router = APIRouter(prefix="/employees", tags=["employees"])

CanRead = Annotated[Principal, Depends(require_permission(Permission.EMPLOYEE_READ))]
CanCreate = Annotated[
    Principal, Depends(require_permission(Permission.EMPLOYEE_WRITE, Permission.SALARY_WRITE))
]


@router.post(
    "",
    status_code=201,
    response_model=EmployeeDetail,
    responses=problem_responses(401, 403, 409),
    summary="Create an employee with their hire salary",
)
def create_employee(
    body: EmployeeCreate,
    principal: CanCreate,
    session: SessionDep,
    request: Request,
    response: Response,
) -> EmployeeDetail:
    employee = service.create_employee(session, principal, body)
    response.headers["Location"] = f"{request.url.path}/{employee.id}"
    return employee


# `:int`, so a sibling path such as /employees/export never reaches this route as an id.
@router.get(
    "/{employee_id:int}",
    response_model=EmployeeDetail,
    responses=problem_responses(401, 403, 404),
    summary="One employee (salary masked without SALARY_READ)",
)
def get_employee(employee_id: int, principal: CanRead, session: SessionDep) -> EmployeeDetail:
    return service.get_employee(session, principal, employee_id)
