"""POST /ask (docs/07-api-spec.md section 12)."""

import time
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from salary_api.core.deps import SessionDep, SettingsDep, require_permission
from salary_api.core.errors import problem_responses
from salary_api.core.permissions import Permission, Principal
from salary_api.modules.ask import service
from salary_api.modules.ask.llm import LLMClient
from salary_api.modules.ask.schemas import AskRequest, AskResponse

router = APIRouter(tags=["ask"])

CanAsk = Annotated[Principal, Depends(require_permission(Permission.ASK))]


def get_sleep() -> Callable[[float], None]:
    """How the service waits before its one provider retry. Tests override it."""
    return time.sleep


def get_llm_client(settings: SettingsDep) -> LLMClient:
    """The configured model; 503 `feature-disabled` without LLM_API_KEY. Tests override it."""
    return service.llm_client(settings)


@router.post(
    "/ask",
    response_model=AskResponse,
    responses=problem_responses(401, 403, 429, 502, 503),
    summary="Ask a question about pay in plain words (audited)",
)
def ask(  # noqa: PLR0913, PLR0917  (one parameter per FastAPI dependency)
    request: AskRequest,
    principal: CanAsk,
    session: SessionDep,
    settings: SettingsDep,
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    sleep: Annotated[Callable[[float], None], Depends(get_sleep)],
) -> AskResponse:
    return service.ask(session, principal, request, llm=llm, settings=settings, sleep=sleep)
