"""POST /ask request and response (docs/07-api-spec.md section 12, docs/glossary.md section 3)."""

from enum import StrEnum
from typing import Any, Final, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from salary_api.core.schemas import Money

# docs/glossary.md section 3: the same caps in the API and the UI.
MAX_MESSAGE_CHARS: Final = 1000
MAX_TURNS: Final = 6


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ChatRole
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class AskRequest(BaseModel):
    """The conversation so far, kept by the client: the last 6 turns, ending with a question."""

    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_TURNS)

    @model_validator(mode="after")
    def _ends_with_a_question(self) -> Self:
        if self.messages[-1].role != ChatRole.USER:
            raise ValueError("The last message must be the user's question.")
        return self


class Figure(BaseModel):
    """A key figure of the answer, as a tool returned it: an amount, or a number (a count,
    a compa-ratio such as `0.93`, a share such as `0.2000`)."""

    label: str
    value: Money | None  # an amount in minor units of its currency
    number: str | None  # a decimal string when the figure is not an amount


class ToolCallTrace(BaseModel):
    """One tool the model called, for "How I got this". Built by the server, not the model."""

    name: str
    args: dict[str, Any]
    ok: bool
    summary: str
    duration_ms: int


class AskResponse(BaseModel):
    answer: str  # markdown, at most MAX_MESSAGE_CHARS, so it can be sent back as history
    figures: list[Figure]
    tool_calls: list[ToolCallTrace]
    caveats: list[str]
    dashboard_link: str | None  # an app path such as /insights/pay-equity?country=DE
