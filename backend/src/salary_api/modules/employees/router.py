from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.employees import service
from salary_api.modules.employees.schemas import (
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListQuery,
    EmployeePage,
    EmployeeUpdate,
    TerminateRequest,
)

router = APIRouter(prefix="/employees", tags=["employees"])

CanRead = Annotated[Principal, Depends(require_permission(Permission.EMPLOYEE_READ))]
CanWrite = Annotated[Principal, Depends(require_permission(Permission.EMPLOYEE_WRITE))]
CanCreate = Annotated[
    Principal, Depends(require_permission(Permission.EMPLOYEE_WRITE, Permission.SALARY_WRITE))
]


@router.get(
    "",
    response_model=EmployeePage,
    responses=problem_responses(401, 403),
    summary="Search, filter, sort and page employees (salary masked without SALARY_READ)",
)
def list_employees(
    query: Annotated[EmployeeListQuery, Query()], principal: CanRead, session: SessionDep
) -> EmployeePage:
    return service.list_employees(session, principal, query)


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


@router.patch(
    "/{employee_id:int}",
    response_model=EmployeeDetail,
    responses=problem_responses(401, 403, 404, 409),
    summary="Edit profile fields (needs the version you read)",
)
def update_employee(
    employee_id: int, body: EmployeeUpdate, principal: CanWrite, session: SessionDep
) -> EmployeeDetail:
    return service.update_employee(session, principal, employee_id, body)


@router.post(
    "/{employee_id:int}/terminate",
    response_model=EmployeeDetail,
    responses=problem_responses(401, 403, 404, 409),
    summary="Terminate an employee (soft delete; history is kept)",
)
def terminate_employee(
    employee_id: int, body: TerminateRequest, principal: CanWrite, session: SessionDep
) -> EmployeeDetail:
    return service.terminate_employee(session, principal, employee_id, body)
