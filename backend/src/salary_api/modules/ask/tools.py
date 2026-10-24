"""The read-only tools the Ask model may call (docs/10 section 4)."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal
from salary_api.modules.ask.llm import ToolCall, ToolSpec


@dataclass(frozen=True, slots=True)
class Reference:
    """Reference data the tool arguments are validated against."""


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    args: dict[str, Any]
    ok: bool
    content: str
    summary: str
    dashboard_link: str | None
    numbers: frozenset[str]


def load_reference(session: Session) -> Reference:
    raise NotImplementedError


def tool_specs(principal: Principal, reference: Reference) -> list[ToolSpec]:
    raise NotImplementedError


class ToolExecutor:
    def __init__(self, session: Session, principal: Principal, reference: Reference) -> None:
        self._session = session

    def execute(self, call: ToolCall) -> ToolResult:
        raise NotImplementedError
