from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from salary_api.core.deps import SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.imports import service
from salary_api.modules.imports.schemas import ImportJobReport

router = APIRouter(prefix="/imports", tags=["imports"])

CanImport = Annotated[Principal, Depends(require_permission(Permission.IMPORT))]


@router.post(
    "",
    status_code=201,
    response_model=ImportJobReport,
    responses=problem_responses(400, 401, 403, 413, 415),
    summary="Upload a CSV or XLSX file and get its dry-run report (nothing is imported yet)",
)
def upload_import(
    file: Annotated[UploadFile, File(description="A .csv (UTF-8) or .xlsx file, at most 4 MB")],
    principal: CanImport,
    session: SessionDep,
    request: Request,
    response: Response,
) -> ImportJobReport:
    report = service.dry_run(session, principal, filename=file.filename, upload=file.file)
    response.headers["Location"] = f"{request.url.path}/{report.id}"
    return report
