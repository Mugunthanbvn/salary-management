"""The production LLMClient: any OpenAI-compatible chat-completions endpoint (docs/10 7).

Gemini (default) and Groq both expose one; the provider is chosen by LLM_BASE_URL alone.
The SDK's own retries are off: the Ask service decides when to retry.
"""

import math
from collections.abc import Sequence
from typing import Final, cast
from urllib.parse import urlsplit

import httpx2
import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolUnionParam

from salary_api.modules.ask.llm import (
    LLMRateLimited,
    LLMResponse,
    LLMUnavailable,
    Message,
    ToolCall,
    ToolSpec,
)

# docs/10 section 6: an output cap per call and a request timeout.
MAX_OUTPUT_TOKENS: Final = 800
TIMEOUT_SECONDS: Final = 25.0

_KNOWN_PROVIDERS: Final = {"generativelanguage.googleapis.com": "gemini", "api.groq.com": "groq"}


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        http_client: httpx2.Client | None = None,
    ) -> None:
        self._model = model
        self._provider = provider_name(base_url)
        self._client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=TIMEOUT_SECONDS,
            max_retries=0,
            http_client=http_client,
        )

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResponse:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=cast("list[ChatCompletionMessageParam]", list(messages)),
                tools=cast("list[ChatCompletionToolUnionParam]", list(tools))
                if tools
                else openai.omit,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
        except openai.RateLimitError as error:
            raise LLMRateLimited(_retry_after(error.response.headers.get("retry-after"))) from None
        except openai.OpenAIError as error:
            # Status, timeout or connection: the type is enough; the body may echo the prompt.
            raise LLMUnavailable(type(error).__name__) from None
        if not completion.choices:
            raise LLMUnavailable("The provider returned no choices.")
        message = completion.choices[0].message
        calls = tuple(
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=call.function.arguments,
                extra=dict(call.model_extra or {}),
            )
            for call in message.tool_calls or ()
            if call.type == "function"
        )
        return LLMResponse(content=message.content, tool_calls=calls)


def provider_name(base_url: str) -> str:
    """`gemini`, `groq`, or the host of any other endpoint (for the audit log)."""
    host = urlsplit(base_url).hostname or "unknown"
    return _KNOWN_PROVIDERS.get(host, host)


def _retry_after(value: str | None) -> int | None:
    """Seconds from a Retry-After header, rounded up; None if absent or not a number."""
    try:
        return math.ceil(float(value)) if value else None
    except ValueError:
        return None
