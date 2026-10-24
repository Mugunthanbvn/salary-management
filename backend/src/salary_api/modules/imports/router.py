from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from salary_api.core.deps import IdPath, SessionDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.imports import service
from salary_api.modules.imports.schemas import ImportCommitResult, ImportJobReport

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


@router.get(
    "/{import_id:int}",
    response_model=ImportJobReport,
    responses=problem_responses(401, 403, 404),
    summary="An import job's report (only for its creator or an administrator)",
)
def get_import(import_id: IdPath, principal: CanImport, session: SessionDep) -> ImportJobReport:
    return service.get_job(session, principal, import_id)


@router.post(
    "/{import_id:int}/commit",
    response_model=ImportCommitResult,
    responses=problem_responses(401, 403, 404, 409, 500),
    summary="Import every row of an error-free dry-run, all or nothing",
)
def commit_import(
    import_id: IdPath, principal: CanImport, session: SessionDep
) -> ImportCommitResult:
    return service.commit(session, principal, import_id)
