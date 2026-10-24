from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.downloads import FILE_RESPONSES, file_response
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.exports import service
from salary_api.modules.exports.schemas import EmployeeExportQuery

router = APIRouter(prefix="/employees", tags=["exports"])

CanExport = Annotated[Principal, Depends(require_permission(Permission.EXPORT))]


# A fixed path: /employees/{employee_id:int} takes integer ids only, so never this one.
@router.get(
    "/export",
    response_class=Response,
    responses=FILE_RESPONSES | problem_responses(401, 403),
    summary="Export the filtered employee list as CSV or XLSX (salary columns need SALARY_READ)",
)
def export_employees(
    query: Annotated[EmployeeExportQuery, Query()], principal: CanExport, session: SessionDep
) -> Response:
    return file_response(service.export_employees(session, principal, query))
