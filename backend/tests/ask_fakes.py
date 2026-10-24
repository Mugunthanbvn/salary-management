"""FakeLLM: a scripted LLMClient for deterministic Ask tests (docs/10 section 10).

It replays a script of responses (tool calls, then a final answer) or raises scripted
errors, and records every request so tests can assert what the model was shown.
"""

import copy
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from salary_api.modules.ask.llm import LLMResponse, Message, ToolCall, ToolSpec


@dataclass(frozen=True)
class Request:
    messages: list[Message]
    tools: list[ToolSpec]

    @property
    def tool_names(self) -> set[str]:
        return {tool["function"]["name"] for tool in self.tools}

    def tool_messages(self) -> list[dict[str, Any]]:
        return [json.loads(m["content"]) for m in self.messages if m["role"] == "tool"]


class FakeLLM:
    provider = "fake"
    model = "fake-model-1"

    def __init__(self, *script: LLMResponse | Exception) -> None:
        self._script = list(script)
        self.requests: list[Request] = []

    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResponse:
        self.requests.append(Request(copy.deepcopy(list(messages)), copy.deepcopy(list(tools))))
        if not self._script:
            raise AssertionError("FakeLLM was called more times than scripted")
        step = self._script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


_call_numbers = iter(range(1, 1_000_000))


def calls(*tool_calls: tuple[str, dict[str, Any] | str]) -> LLMResponse:
    """One model turn that asks for these tools: calls(("get_fx_rates", {}))."""
    return LLMResponse(
        content=None,
        tool_calls=tuple(
            ToolCall(
                id=f"call-{next(_call_numbers)}",
                name=name,
                arguments=args if isinstance(args, str) else json.dumps(args),
            )
            for name, args in tool_calls
        ),
    )


def call(name: str, args: dict[str, Any] | str | None = None) -> LLMResponse:
    return calls((name, {} if args is None else args))


def answer(
    text: str = "Here is the answer.",
    *,
    figures: Sequence[dict[str, Any]] = (),
    caveats: Sequence[str] = (),
) -> LLMResponse:
    """A final answer in the AskAnswer JSON format the system prompt asks for."""
    body = {"answer": text, "figures": list(figures), "caveats": list(caveats)}
    return LLMResponse(content=json.dumps(body))


def text(content: str) -> LLMResponse:
    return LLMResponse(content=content)
