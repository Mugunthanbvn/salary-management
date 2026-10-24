"""The production LLMClient: any OpenAI-compatible chat-completions endpoint (docs/10 7)."""

from collections.abc import Sequence

import httpx

from salary_api.modules.ask.llm import LLMResponse, Message, ToolSpec


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._model = model

    @property
    def provider(self) -> str:
        raise NotImplementedError

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResponse:
        raise NotImplementedError
