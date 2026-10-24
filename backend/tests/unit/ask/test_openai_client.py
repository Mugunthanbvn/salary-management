"""The OpenAI-compatible adapter (docs/10 section 7), against a mocked HTTP transport.

No request leaves the process: httpx2.MockTransport answers in memory.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from salary_api.modules.ask.llm import LLMRateLimited, LLMUnavailable, ToolCall
from salary_api.modules.ask.openai_client import OpenAICompatibleLLMClient

BASE_URL = "https://llm.example/v1beta/openai/"
TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": "get_fx_rates", "parameters": {"type": "object"}}}
]


def _client(handler: Callable[[httpx2.Request], httpx2.Response]) -> OpenAICompatibleLLMClient:
    return OpenAICompatibleLLMClient(
        base_url=BASE_URL,
        api_key="test-key",
        model="test-model",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )


def _completion(message: dict[str, Any]) -> httpx2.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "test-model",
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
    }
    return httpx2.Response(200, json=body)


def test_sends_the_model_messages_tools_and_an_output_cap() -> None:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        assert str(request.url) == f"{BASE_URL}chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        return _completion({"role": "assistant", "content": "{}"})

    _client(handler).complete([{"role": "user", "content": "Hi"}], TOOLS)

    assert sent[0]["model"] == "test-model"
    assert sent[0]["messages"] == [{"role": "user", "content": "Hi"}]
    assert sent[0]["tools"] == TOOLS
    assert sent[0]["max_tokens"] == 800


def test_leaves_tools_out_when_there_are_none() -> None:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        return _completion({"role": "assistant", "content": "{}"})

    _client(handler).complete([{"role": "user", "content": "Hi"}], [])

    assert "tools" not in sent[0]


def test_returns_the_text_of_a_final_answer() -> None:
    response = _client(lambda _: _completion({"role": "assistant", "content": "Done"})).complete(
        [{"role": "user", "content": "Hi"}], TOOLS
    )

    assert (response.content, response.tool_calls) == ("Done", ())


def test_returns_the_tool_calls_the_model_asks_for() -> None:
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "get_fx_rates", "arguments": "{}"},
            }
        ],
    }

    response = _client(lambda _: _completion(message)).complete(
        [{"role": "user", "content": "Hi"}], TOOLS
    )

    assert response.content is None
    assert response.tool_calls == (ToolCall(id="call-1", name="get_fx_rates", arguments="{}"),)


def test_a_provider_429_is_rate_limited_with_its_retry_after() -> None:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, headers={"retry-after": "2.5"}, json={"error": {}})

    with pytest.raises(LLMRateLimited) as raised:
        _client(handler).complete([{"role": "user", "content": "Hi"}], TOOLS)

    assert raised.value.retry_after_seconds == 3  # rounded up


def test_a_provider_429_without_retry_after_has_no_wait() -> None:
    with pytest.raises(LLMRateLimited) as raised:
        _client(lambda _: httpx2.Response(429, json={"error": {}})).complete(
            [{"role": "user", "content": "Hi"}], TOOLS
        )

    assert raised.value.retry_after_seconds is None


@pytest.mark.parametrize("status", [400, 401, 404, 500, 503])
def test_any_other_provider_error_is_unavailable(status: int) -> None:
    with pytest.raises(LLMUnavailable):
        _client(lambda _: httpx2.Response(status, json={"error": {}})).complete(
            [{"role": "user", "content": "Hi"}], TOOLS
        )


def test_a_timeout_is_unavailable() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    with pytest.raises(LLMUnavailable):
        _client(handler).complete([{"role": "user", "content": "Hi"}], TOOLS)


def test_a_response_without_choices_is_unavailable() -> None:
    body = {"id": "1", "object": "chat.completion", "created": 1, "model": "m", "choices": []}

    with pytest.raises(LLMUnavailable):
        _client(lambda _: httpx2.Response(200, json=body)).complete(
            [{"role": "user", "content": "Hi"}], TOOLS
        )


@pytest.mark.parametrize(
    ("base_url", "provider"),
    [
        ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini"),
        ("https://api.groq.com/openai/v1", "groq"),
        ("http://localhost:11434/v1", "localhost"),
    ],
)
def test_names_the_provider_from_the_base_url(base_url: str, provider: str) -> None:
    client = OpenAICompatibleLLMClient(base_url=base_url, api_key="k", model="m")

    assert (client.provider, client.model) == (provider, "m")
