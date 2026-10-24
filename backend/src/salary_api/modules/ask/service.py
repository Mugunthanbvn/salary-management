"""Ask about pay: the tool-calling loop (docs/10 sections 3, 6, 7 and 9).

One question is: the per-user limit check; an `ask.query` audit event, committed before the
model is called so a burst of parallel questions is counted (then the limit is checked
again, like the login limit, docs/08 section 9); up to ASK_MAX_STEPS model round trips with
tool calls; a final answer in the AskAnswer JSON format (one repair retry); and an
`ask.answer` audit event with the outcome, whether the question was answered or not.

No transaction is open while the model is called: on SQLite a write transaction holds the
database lock, which would block every other writer for the length of a model call.

Figures are grounded: a figure whose number (and currency) no tool returned is dropped
with a caveat, so the model cannot present a number of its own (docs/10 section 6).
"""

import json
import math
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Final

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.errors import FeatureDisabled, RateLimited, UpstreamUnavailable
from salary_api.core.models import utc_now
from salary_api.core.permissions import Principal
from salary_api.core.schemas import Money
from salary_api.domain.currency import SUPPORTED_CURRENCIES
from salary_api.modules.ask.llm import (
    LLMClient,
    LLMRateLimited,
    LLMResponse,
    LLMUnavailable,
    Message,
    ToolSpec,
)
from salary_api.modules.ask.openai_client import OpenAICompatibleLLMClient
from salary_api.modules.ask.prompt import system_prompt
from salary_api.modules.ask.schemas import (
    MAX_MESSAGE_CHARS,
    AskRequest,
    AskResponse,
    Figure,
    ToolCallTrace,
)
from salary_api.modules.ask.tools import (
    ToolExecutor,
    ToolResult,
    load_reference,
    normalise_number,
    tool_error,
    tool_specs,
)
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.audit.service import AuditAction, events_since, record_event

_logger = structlog.get_logger(__name__)

RATE_LIMIT_WINDOW: Final = timedelta(hours=1)
MAX_PROVIDER_RETRY_WAIT: Final = 3  # seconds; a longer Retry-After goes back to the user
NO_RETRY_AFTER_WAIT: Final = 2  # seconds before the one retry when the provider gave none
DEFAULT_RETRY_AFTER: Final = 10  # seconds, when the provider gave no Retry-After
QUESTION_DEADLINE_SECONDS: Final = 60.0  # no new tool step starts after this
MAX_TOOL_CALLS_PER_REPLY: Final = 5
AUDITED_QUESTION_CHARS: Final = 200
MAX_FIGURES: Final = 4
MAX_CAVEATS: Final = 3
MAX_CAVEAT_CHARS: Final = 200

STEP_LIMIT_CAVEAT: Final = "I couldn't complete this analysis; try narrowing the question."
STEP_LIMIT_NOTE: Final = (
    "The tool step limit is reached. Answer now in the JSON format with what you have."
)
REPAIR_NOTE: Final = (
    "Your last reply was not valid AskAnswer JSON ({error}). Reply again with only the "
    'JSON object: {{"answer": ..., "figures": [...], "caveats": [...]}}.'
)
FIGURES_REMOVED_CAVEAT: Final = (
    "{count} figure(s) the assistant gave did not match the data and were removed."
)
TOO_MANY_CALLS: Final = (
    f"At most {MAX_TOOL_CALLS_PER_REPLY} tool calls per reply; this one was not run."
)


class Outcome(StrEnum):
    """`diff.outcome` of the ask.answer audit event."""

    ANSWERED = "answered"
    STEP_LIMIT = "step_limit"
    INVALID_OUTPUT = "invalid_output"
    UPSTREAM_RATE_LIMITED = "upstream_rate_limited"
    UPSTREAM_ERROR = "upstream_error"


def llm_client(settings: Settings) -> LLMClient:
    """The configured provider. Ask is switched off while LLM_API_KEY is empty."""
    api_key = settings.llm_api_key.get_secret_value()
    if not api_key:
        raise FeatureDisabled("Ask is turned off on this deployment: no LLM_API_KEY is set.")
    return OpenAICompatibleLLMClient(
        base_url=settings.llm_base_url, api_key=api_key, model=settings.llm_model
    )


def ask(  # noqa: PLR0913
    session: Session,
    principal: Principal,
    request: AskRequest,
    *,
    llm: LLMClient,
    settings: Settings,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> AskResponse:
    """Answer the last question of the conversation with the caller's tools.

    Raises RateLimited (the caller's hourly limit, or the provider's after one retry) and
    UpstreamUnavailable (provider failure, or invalid output after one repair retry).
    """
    now = utc_now()
    _refuse_over_the_limit(session, principal, settings, now=now, recorded_before=None)
    reference = load_reference(session)
    query = record_event(
        session,
        actor_id=principal.user_id,
        action=AuditAction.ASK_QUERY,
        entity="ask",
        entity_id=None,
        diff={
            "question": request.messages[-1].content[:AUDITED_QUESTION_CHARS],
            "provider": llm.provider,
            "model": llm.model,
        },
    )
    session.commit()  # counted from now on, and no transaction stays open
    _refuse_over_the_limit(session, principal, settings, now=now, recorded_before=query.id)
    session.commit()
    conversation = _Conversation(
        session=session,
        llm=llm,
        tools=tool_specs(principal, reference),
        executor=ToolExecutor(session, principal, reference),
        messages=[
            {"role": "system", "content": system_prompt(reference, today=now.date())},
            *({"role": m.role.value, "content": m.content} for m in request.messages),
        ],
        sleep=sleep,
        clock=clock,
        deadline=clock() + QUESTION_DEADLINE_SECONDS,
        budget=settings.ask_max_steps + 1,  # the tool steps and one answer, repair included
    )
    try:
        answer, outcome = conversation.run(settings.ask_max_steps)
    except LLMRateLimited as error:
        _audit_answer(session, query, conversation, Outcome.UPSTREAM_RATE_LIMITED)
        raise RateLimited(
            "The assistant is busy. Try again shortly.",
            retry_after_seconds=error.retry_after_seconds or DEFAULT_RETRY_AFTER,
        ) from None
    except LLMUnavailable as error:
        _logger.warning("ask_upstream_error", error=str(error), provider=llm.provider)
        _audit_answer(session, query, conversation, Outcome.UPSTREAM_ERROR)
        raise UpstreamUnavailable("The assistant is unavailable right now.") from None
    except _InvalidOutput:
        _audit_answer(session, query, conversation, Outcome.INVALID_OUTPUT)
        raise UpstreamUnavailable("The assistant gave an answer that could not be read.") from None
    except Exception:
        session.rollback()  # whatever broke, the outcome is still recorded
        _audit_answer(session, query, conversation, Outcome.UPSTREAM_ERROR)
        raise
    _audit_answer(session, query, conversation, outcome)
    return _response(answer, conversation.results, outcome)


# --- The per-user limit (docs/08 section 9): counted from ask.query events


def _refuse_over_the_limit(
    session: Session,
    principal: Principal,
    settings: Settings,
    *,
    now: datetime,
    recorded_before: int | None,
) -> None:
    """429 when the caller has asked ASK_RATE_LIMIT_PER_HOUR questions in the last hour.

    `recorded_before`: count only the questions recorded before this event id (the caller's
    own, just committed), so of a parallel burst only the first ones get through.
    """
    events = [
        event
        for event in events_since(
            session,
            action=AuditAction.ASK_QUERY,
            since=now - RATE_LIMIT_WINDOW,
            actor_id=principal.user_id,
        )
        if recorded_before is None or event.id < recorded_before
    ]
    limit = settings.ask_rate_limit_per_hour
    if len(events) >= limit:
        # A slot frees when the oldest question that still counts is an hour old.
        frees_at = events[len(events) - limit].at + RATE_LIMIT_WINDOW
        session.commit()  # end the read before answering
        raise RateLimited(
            f"You have asked {limit} questions in the last hour, the hourly limit.",
            retry_after_seconds=max(1, math.ceil((frees_at - now).total_seconds())),
        )


# --- The conversation with the model


class _InvalidOutput(Exception):
    """The final answer was not AskAnswer JSON, even after the repair retry."""


class _ModelFigure(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = Field(min_length=1, max_length=120)
    amount_minor: int | None = None
    currency: str | None = None
    value: str | int | Decimal | None = None  # JSON numbers arrive as int or Decimal


class _ModelAnswer(BaseModel):
    """The AskAnswer format of docs/10 section 5, as the model writes it.

    Figures stay raw here: a bad figure is dropped on its own, it does not spoil the answer.
    """

    model_config = ConfigDict(extra="ignore")

    answer: str = Field(min_length=1)
    figures: list[Any] = Field(default_factory=list[Any])
    caveats: list[str] = Field(default_factory=list[str])


@dataclass
class _Answer:
    model: _ModelAnswer
    caveats: list[str] = field(default_factory=list[str])


@dataclass
class _Conversation:
    session: Session
    llm: LLMClient
    tools: list[ToolSpec]
    executor: ToolExecutor
    messages: list[Message]
    sleep: Callable[[float], None]
    clock: Callable[[], float]
    deadline: float
    budget: int  # model calls in all
    results: list[ToolResult] = field(default_factory=list[ToolResult])
    steps: int = 0
    calls: int = 0
    started: float = field(default_factory=time.perf_counter)

    def run(self, max_steps: int) -> tuple[_Answer, Outcome]:
        while self.steps < max_steps and self.clock() < self.deadline:
            response = self._complete(self.tools)
            if not response.tool_calls:
                return _Answer(self._final(response)), Outcome.ANSWERED
            self.steps += 1
            self._run_tools(response)
        # Out of steps or time: one last call without tools, so the model can only answer.
        self.messages.append({"role": "user", "content": STEP_LIMIT_NOTE})
        response = self._complete([])
        parsed = None if response.tool_calls else _parse_answer(response.content)
        fallback = _ModelAnswer(answer=STEP_LIMIT_CAVEAT)
        return _Answer(parsed or fallback, [STEP_LIMIT_CAVEAT]), Outcome.STEP_LIMIT

    def _complete(self, tools: Sequence[ToolSpec]) -> LLMResponse:
        """One round trip; a provider 429 with a short (or no) Retry-After is retried once."""
        self.calls += 1
        try:
            return self.llm.complete(self.messages, tools)
        except LLMRateLimited as error:
            wait = error.retry_after_seconds
            if wait is not None and wait > MAX_PROVIDER_RETRY_WAIT:
                raise
            self.sleep(NO_RETRY_AFTER_WAIT if wait is None else wait)
            return self.llm.complete(self.messages, tools)

    def _run_tools(self, response: LLMResponse) -> None:
        self.messages.append(
            {
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                        **call.extra,
                    }
                    for call in response.tool_calls
                ],
            }
        )
        for index, call in enumerate(response.tool_calls):
            if index < MAX_TOOL_CALLS_PER_REPLY:
                result = self.executor.execute(call)
                self.results.append(result)
                content = result.content
            else:
                content = tool_error("too_many_calls", TOO_MANY_CALLS)
            # A tool message: data for the model, never part of its instructions.
            self.messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        self.session.commit()  # keep what the tools audited; nothing open during the next call

    def _final(self, response: LLMResponse) -> _ModelAnswer:
        """The answer, after one repair retry (without tools) if it is not AskAnswer JSON."""
        parsed = _parse_answer(response.content)
        if parsed is not None:
            return parsed
        if self.calls >= self.budget:
            raise _InvalidOutput
        self.messages.append({"role": "assistant", "content": response.content or ""})
        self.messages.append(
            {"role": "user", "content": REPAIR_NOTE.format(error="not a JSON object")}
        )
        retry = self._complete([])
        parsed = None if retry.tool_calls else _parse_answer(retry.content)
        if parsed is None:
            raise _InvalidOutput
        return parsed


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _parse_answer(content: str | None) -> _ModelAnswer | None:
    if not content:
        return None
    text = content.strip()
    if fenced := _FENCE.match(text):
        text = fenced.group(1)
    try:
        return _ModelAnswer.model_validate(json.loads(text, parse_float=Decimal))
    except (json.JSONDecodeError, ValidationError):
        return None


# --- The response


def _response(answer: _Answer, results: Sequence[ToolResult], outcome: Outcome) -> AskResponse:
    amounts = frozenset[tuple[str, str]]().union(*(result.amounts for result in results))
    numbers = frozenset[str]().union(*(result.numbers for result in results))
    figures = [_figure(figure) for figure in answer.model.figures[:MAX_FIGURES]]
    grounded = [
        figure for figure in figures if figure is not None and _grounded(figure, amounts, numbers)
    ]
    caveats = [_cut(caveat, MAX_CAVEAT_CHARS) for caveat in answer.model.caveats[:MAX_CAVEATS]]
    if removed := len(figures) - len(grounded):
        caveats.append(FIGURES_REMOVED_CAVEAT.format(count=removed))
    caveats += [caveat for caveat in answer.caveats if caveat not in caveats]
    links = [result.dashboard_link for result in results if result.ok and result.dashboard_link]
    _logger.info("ask_answered", outcome=outcome.value, tools=len(results))
    return AskResponse(
        answer=_cut(answer.model.answer, MAX_MESSAGE_CHARS),
        figures=grounded,
        tool_calls=[
            ToolCallTrace(
                name=result.name,
                args=result.args,
                ok=result.ok,
                summary=result.summary,
                duration_ms=result.duration_ms,
            )
            for result in results
        ],
        caveats=caveats,
        dashboard_link=links[-1] if links else None,
    )


def _figure(raw: object) -> Figure | None:
    """A money figure (amount_minor + a supported currency) or a number; None otherwise."""
    try:
        figure = _ModelFigure.model_validate(raw)
    except ValidationError:
        return None
    if figure.amount_minor is not None and figure.currency in SUPPORTED_CURRENCIES:
        money = Money(amount_minor=figure.amount_minor, currency=figure.currency)
        return Figure(label=figure.label, value=money, number=None)
    if figure.value is None:
        return None
    try:
        number = normalise_number(str(figure.value))
    except InvalidOperation:
        return None
    return Figure(label=figure.label, value=None, number=number)


def _grounded(figure: Figure, amounts: frozenset[tuple[str, str]], numbers: frozenset[str]) -> bool:
    """An amount must match a tool's amount in the same currency; a number a tool's number."""
    if figure.value is not None:
        pair = (normalise_number(str(figure.value.amount_minor)), figure.value.currency)
        return pair in amounts
    return figure.number in numbers


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --- Audit (docs/10 section 9): the question and tool names, never tool results


def _audit_answer(
    session: Session, query: AuditEvent, conversation: _Conversation, outcome: Outcome
) -> None:
    record_event(
        session,
        actor_id=query.actor_id,
        action=AuditAction.ASK_ANSWER,
        entity="ask",
        entity_id=query.id,
        diff={
            "tools": [result.name for result in conversation.results],
            "steps": conversation.steps,
            "latency_ms": round((time.perf_counter() - conversation.started) * 1000),
            "outcome": outcome.value,
        },
    )
    session.commit()
