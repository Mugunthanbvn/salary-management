"""The model behind Ask, as an interface (docs/10 section 7, ADR 0015).

Production uses the OpenAI-compatible adapter (`openai_client.py`); tests use a scripted
`FakeLLM` (tests/ask_fakes.py), so CI never touches the network.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

# OpenAI chat-completions shapes: {"role": ..., "content": ...} and function tools.
type Message = dict[str, Any]
type ToolSpec = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One tool the model asks for. `arguments` is the model's raw JSON text."""

    id: str
    name: str
    arguments: str
    # Provider-specific fields of the call (Gemini's thought signature), sent back as is.
    extra: Mapping[str, Any] = field(default_factory=dict[str, Any])


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Either tool calls to run, or the final text (`content`)."""

    content: str | None
    tool_calls: tuple[ToolCall, ...] = field(default=())


class LLMClient(Protocol):
    @property
    def provider(self) -> str:
        """A short provider name for the audit log, e.g. `gemini`."""
        ...

    @property
    def model(self) -> str: ...

    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResponse:
        """One chat-completions round trip. Raises LLMRateLimited or LLMUnavailable."""
        ...


class LLMError(Exception):
    """The provider did not give a usable answer."""


class LLMRateLimited(LLMError):
    """The provider answered 429. `retry_after_seconds` is its Retry-After, if it sent one."""

    def __init__(self, retry_after_seconds: int | None) -> None:
        super().__init__("The LLM provider is rate limiting requests.")
        self.retry_after_seconds = retry_after_seconds


class LLMUnavailable(LLMError):
    """Any other failure: 4xx, 5xx, timeout, connection error, or an empty response."""
