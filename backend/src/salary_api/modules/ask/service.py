"""Ask about pay: the tool-calling loop (docs/10 sections 3, 6 and 9)."""

import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.permissions import Principal
from salary_api.modules.ask.llm import LLMClient
from salary_api.modules.ask.schemas import AskRequest, AskResponse


def ask(  # noqa: PLR0913
    session: Session,
    principal: Principal,
    request: AskRequest,
    *,
    llm: LLMClient,
    settings: Settings,
    sleep: Callable[[float], None] = time.sleep,
) -> AskResponse:
    raise NotImplementedError
