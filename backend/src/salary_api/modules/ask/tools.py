"""The read-only tools the Ask model may call (docs/10 section 4, docs/08 section 8).

Each tool is a thin wrapper over an insight, employee or reference service, so every
number matches the dashboard and the services' masking and small-group rule apply.

Roles are enforced in layers: `tool_specs` offers the model only the tools the caller's
permissions allow; `ToolExecutor.execute` re-checks the permission of every call before
anything is fetched; the services then mask and suppress. Arguments are validated against
the reference data (countries, departments, job roles) and the glossary enums; a bad
argument is a tool error the model can read and fix, never an exception.

Tool results go back to the model as `tool` messages: data, never instructions.
"""

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Final, cast
from urllib.parse import urlencode

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from salary_api.core.errors import Forbidden, ProblemError
from salary_api.core.permissions import Permission, Principal
from salary_api.core.schemas import Comp
from salary_api.domain.enums import EmploymentType, Level
from salary_api.modules.ask.llm import ToolCall, ToolSpec
from salary_api.modules.employees import service as employees
from salary_api.modules.employees.schemas import EmployeeListQuery
from salary_api.modules.insights import service as insights
from salary_api.modules.insights.schemas import (
    CompareMetric,
    Direction,
    InsightQuery,
    JobTitleQuery,
    PayEquityCohorts,
    PayEquityQuery,
    PayEquityView,
    TopEarnersQuery,
)
from salary_api.modules.reference import service as reference_service

_logger = structlog.get_logger(__name__)

MAX_TOP_EARNERS_FOR_ASK: Final = 20  # fewer than the API's 50: tokens, and data minimisation
MAX_SEARCH_RESULTS: Final = 10
MAX_FLAGGED_COHORTS: Final = 10


class ToolArgumentError(Exception):
    """An argument the model can fix: an unknown value, or a missing one."""


@dataclass(frozen=True, slots=True)
class Reference:
    """Reference data the tool arguments are validated against, read once per question."""

    countries: tuple[str, ...]  # codes, in the reference data's order (by name)
    country_labels: Mapping[str, str]  # code -> "Germany (EUR)"
    departments: Mapping[str, int]  # name -> id
    job_roles: Mapping[str, int]  # title -> id


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What one call returned: `content` goes to the model, the rest to the response."""

    name: str
    args: dict[str, Any]
    ok: bool
    content: str  # JSON: {"ok": true, "data": ...} or {"ok": false, "error": {code, message}}
    summary: str
    dashboard_link: str | None
    # For checking the answer's figures: (amount, currency) pairs and the other numbers.
    amounts: frozenset[tuple[str, str]]
    numbers: frozenset[str]
    duration_ms: int = 0


def load_reference(session: Session) -> Reference:
    data = reference_service.reference_data(session)
    return Reference(
        countries=tuple(country.code for country in data.countries),
        country_labels={
            country.code: f"{country.name} ({country.default_currency})"
            for country in data.countries
        },
        departments={department.name: department.id for department in data.departments},
        job_roles={role.title: role.id for role in data.job_roles},
    )


# --- Arguments: what the model sends. Names, not ids; resolved against Reference.


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Filters(_Args):
    """Who a figure covers. Defaults: full-time, active employees, base pay."""

    country: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    job_role: str | None = Field(default=None, max_length=100)
    level: Level | None = None
    employment_type: list[EmploymentType] = Field(
        default_factory=lambda: [EmploymentType.FULL_TIME]
    )
    comp: Comp = Comp.BASE


class GroupBy(StrEnum):
    DEPARTMENT = "department"
    JOB_ROLE = "job_role"
    COUNTRY = "country"


class _PopulationArgs(_Args):
    filters: Filters = Field(default_factory=Filters)


class _GroupArgs(_PopulationArgs):
    group_by: GroupBy


class _CompareArgs(_Args):
    a: Filters
    b: Filters
    metric: CompareMetric = CompareMetric.MEDIAN


class _TopEarnersArgs(_Args):
    country: str
    n: int = Field(default=5, ge=1, le=MAX_TOP_EARNERS_FOR_ASK)
    direction: Direction = Direction.TOP
    comp: Comp = Comp.BASE


class _SearchArgs(_Args):
    query: str = Field(min_length=2, max_length=64)
    limit: int = Field(default=5, ge=1, le=MAX_SEARCH_RESULTS)


class _NoArgs(_Args):
    pass


def _country(reference: Reference, code: str) -> str:
    if code not in reference.countries:
        raise ToolArgumentError(f"Unknown country {code!r}. Use one of the listed codes.")
    return code


def _query(reference: Reference, filters: Filters) -> InsightQuery:
    """The insight query for these filters, refusing values the reference data lacks."""
    department_ids: list[int] = []
    if filters.department is not None:
        if filters.department not in reference.departments:
            raise ToolArgumentError(
                f"Unknown department {filters.department!r}. Use one of the listed names."
            )
        department_ids.append(reference.departments[filters.department])
    job_role_ids: list[int] = []
    if filters.job_role is not None:
        if filters.job_role not in reference.job_roles:
            raise ToolArgumentError(
                f"Unknown job role {filters.job_role!r}. Use one of the listed titles."
            )
        job_role_ids.append(reference.job_roles[filters.job_role])
    return InsightQuery(
        country=[] if filters.country is None else [_country(reference, filters.country)],
        department_id=department_ids,
        job_role_id=job_role_ids,
        level=[] if filters.level is None else [filters.level],
        employment_type=filters.employment_type,
        comp=filters.comp,
    )


def _link(path: str, query: InsightQuery | None = None, **extra: str) -> str:
    """A dashboard URL: the page's parameters use the API's names (docs/13 section 3)."""
    params: list[tuple[str, str]] = []
    if query is not None:
        params += [("country", code) for code in query.country]
        params += [("department_id", str(id_)) for id_ in query.department_id]
        params += [("job_role_id", str(id_)) for id_ in query.job_role_id]
        params += [("level", level.value) for level in query.level]
    params += list(extra.items())
    return f"{path}?{urlencode(params)}" if params else path


# --- The tools


@dataclass(frozen=True, slots=True)
class _Output:
    data: dict[str, Any]
    summary: str
    dashboard_link: str | None = None


type _Run = Callable[[Session, Principal, Reference, Any], _Output]


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    permissions: frozenset[Permission]
    args: type[_Args]
    parameters: Callable[[Reference], dict[str, Any]]
    run: _Run = field(repr=False)


def _dump(model: BaseModel, *exclude: str) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude={"population", *exclude})


def _count(value: int | None, noun: str) -> str:
    return f"{noun}: hidden (small group)" if value is None else f"{value:,} {noun}"


def _overview(session: Session, principal: Principal, ref: Reference, args: Any) -> _Output:
    query = _query(ref, args.filters)
    result = insights.overview(session, principal, query)
    return _Output(_dump(result), _count(result.headcount, "employees"), _link("/insights", query))


def _by_group(session: Session, principal: Principal, ref: Reference, args: Any) -> _Output:
    query = _query(ref, args.filters)
    link = _link("/insights", query)
    if args.group_by == GroupBy.DEPARTMENT:
        by_department = insights.by_department(session, principal, query)
        data = _dump(by_department)
        return _Output(data, f"{len(by_department.groups)} departments", link)
    if args.group_by == GroupBy.COUNTRY:
        overview = insights.overview(session, principal, query)
        data = {
            "currency": "local and USD",
            "fx_as_of": None if overview.fx_as_of is None else overview.fx_as_of.isoformat(),
            "groups": [group.model_dump(mode="json") for group in overview.by_country],
        }
        return _Output(data, f"{len(overview.by_country)} countries", link)
    if len(query.country) != 1:
        raise ToolArgumentError(
            "group_by=job_role needs filters.country: titles compare in one market."
        )
    by_title = insights.by_job_title(
        session,
        principal,
        JobTitleQuery(
            country=query.country[0],
            department_id=query.department_id,
            job_role_id=query.job_role_id,
            level=query.level,
            employment_type=query.employment_type,
            comp=query.comp,
        ),
    )
    return _Output(_dump(by_title), f"{len(by_title.groups)} job roles", link)


def _compare(session: Session, principal: Principal, ref: Reference, args: Any) -> _Output:
    a, b = _query(ref, args.a), _query(ref, args.b)
    result = insights.compare_groups(session, principal, a, b, args.metric)
    summary = (
        f"{args.metric.value}: hidden (small group)"
        if result.pct_difference is None
        else f"{args.metric.value}: a vs b {Decimal(result.pct_difference) * 100:+.1f} %"
    )
    return _Output(_dump(result), summary, _link("/insights", a))


def _pay_equity(session: Session, principal: Principal, ref: Reference, args: Any) -> _Output:
    query = _query(ref, args.filters)
    one_country = len(query.country) == 1
    result = insights.pay_equity(
        session,
        principal,
        PayEquityQuery(
            view=PayEquityView.DEPARTMENTS if one_country else PayEquityView.COHORTS,
            country=query.country,
            department_id=query.department_id,
            job_role_id=query.job_role_id,
            level=query.level,
            employment_type=query.employment_type,
        ),
    )
    summary = result.summary
    text = (
        f"{_count(summary.employees_flagged_underpaid, 'below band')}, "
        f"{_count(summary.employees_flagged_overpaid, 'above band')}"
    )
    link = _link("/insights/pay-equity", query)
    if not isinstance(result, PayEquityCohorts):
        return _Output(_dump(result), text, link)
    # Every cohort would cost thousands of tokens: send the most flagged ones only.
    flagged = sorted(
        (c for c in result.cohorts if (c.underpaid_count or 0) + (c.overpaid_count or 0) > 0),
        key=lambda c: -((c.underpaid_count or 0) + (c.overpaid_count or 0)),
    )
    data = {
        "thresholds": result.thresholds.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "cohorts_evaluated": len(result.cohorts),
        "flagged_cohorts": [
            cohort.model_dump(mode="json") for cohort in flagged[:MAX_FLAGGED_COHORTS]
        ],
    }
    return _Output(data, text, link)


def _top_earners(session: Session, principal: Principal, ref: Reference, args: Any) -> _Output:
    country = _country(ref, args.country)
    result = insights.top_earners(
        session,
        principal,
        TopEarnersQuery(country=country, n=args.n, direction=args.direction, comp=args.comp),
    )
    return _Output(
        _dump(result), f"{len(result.items)} people", _link("/insights", country=country)
    )


def _search(session: Session, principal: Principal, _ref: Reference, args: Any) -> _Output:
    page = employees.list_employees(
        session, principal, EmployeeListQuery(q=args.query, page_size=args.limit)
    )
    items = [
        {
            "employee_code": item.employee_code,
            "first_name": item.first_name,
            "last_name": item.last_name,
            "job_role": item.job_role.title,
            "level": item.level.value,
            "department": item.department.name,
            "country_code": item.country_code,
            "current_base": None
            if item.current_base is None
            else item.current_base.model_dump(mode="json"),
        }
        for item in page.items
    ]
    return _Output(
        {"total": page.total, "items": items},
        f"{page.total:,} matches",
        _link("/employees", q=args.query),
    )


def _fx_rates(session: Session, _principal: Principal, _ref: Reference, _args: Any) -> _Output:
    result = reference_service.fx_rates(session)
    return _Output(result.model_dump(mode="json"), f"{len(result.rates)} rates")


# --- JSON schemas the model sees, with enums from the reference data


def _filters_schema(ref: Reference, *, with_comp: bool = True) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "country": {"type": "string", "enum": list(ref.countries), "description": "ISO code"},
        "department": {"type": "string", "enum": sorted(ref.departments)},
        "job_role": {"type": "string", "enum": sorted(ref.job_roles)},
        "level": {"type": "string", "enum": [level.value for level in Level]},
        "employment_type": {
            "type": "array",
            "items": {"type": "string", "enum": [kind.value for kind in EmploymentType]},
            "description": "Default: FULL_TIME only",
        },
    }
    if with_comp:
        properties["comp"] = {
            "type": "string",
            "enum": [comp.value for comp in Comp],
            "description": "base (default) or total = base + allowances + target bonus",
        }
    return {"type": "object", "properties": properties, "additionalProperties": False}


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _enum(values: type[StrEnum]) -> dict[str, Any]:
    return {"type": "string", "enum": [value.value for value in values]}


_INSIGHTS: Final = frozenset({Permission.ASK, Permission.INSIGHTS_READ})
_INDIVIDUALS: Final = frozenset({Permission.ASK, Permission.SALARY_READ})

TOOLS: Final[tuple[Tool, ...]] = (
    Tool(
        "get_pay_overview",
        "Headcount, total payroll (USD) and pay statistics for one population, with each "
        "country's statistics in local currency and USD.",
        _INSIGHTS,
        _PopulationArgs,
        lambda ref: _object({"filters": _filters_schema(ref)}),
        _overview,
    ),
    Tool(
        "get_pay_by_group",
        "Pay statistics per department, per country, or per job role (job_role needs "
        "filters.country).",
        _INSIGHTS,
        _GroupArgs,
        lambda ref: _object(
            {"group_by": _enum(GroupBy), "filters": _filters_schema(ref)}, ["group_by"]
        ),
        _by_group,
    ),
    Tool(
        "compare_groups",
        "Compare one metric between population a and population b. Returns a, b, the "
        "difference a - b and pct_difference ((a - b) / b, 0.2000 = 20 %). Use it for every "
        "difference: never compute one yourself.",
        _INSIGHTS,
        _CompareArgs,
        lambda ref: _object(
            {"a": _filters_schema(ref), "b": _filters_schema(ref), "metric": _enum(CompareMetric)},
            ["a", "b", "metric"],
        ),
        _compare,
    ),
    Tool(
        "get_pay_equity_outliers",
        "Base pay against pay bands (compa-ratio = base / band midpoint; below 0.80 is "
        "underpaid, above 1.20 overpaid). With exactly one country: per-department median "
        "compa-ratio, below_threshold when under 0.95. Otherwise: the most flagged cohorts.",
        _INSIGHTS,
        _PopulationArgs,
        lambda ref: _object({"filters": _filters_schema(ref, with_comp=False)}),
        _pay_equity,
    ),
    Tool(
        "get_top_earners",
        "The highest (or lowest) paid people in one country, in its currency.",
        _INDIVIDUALS,
        _TopEarnersArgs,
        lambda ref: _object(
            {
                "country": {"type": "string", "enum": list(ref.countries)},
                "n": {"type": "integer", "minimum": 1, "maximum": MAX_TOP_EARNERS_FOR_ASK},
                "direction": _enum(Direction),
                "comp": _enum(Comp),
            },
            ["country"],
        ),
        _top_earners,
    ),
    Tool(
        "search_employees",
        "Find employees by name, employee code or email; returns their role and current pay.",
        _INDIVIDUALS,
        _SearchArgs,
        lambda _ref: _object(
            {
                "query": {"type": "string", "minLength": 2, "maxLength": 64},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_RESULTS},
            },
            ["query"],
        ),
        _search,
    ),
    Tool(
        "get_fx_rates",
        "The current USD exchange rates and their as_of date.",
        frozenset({Permission.ASK}),
        _NoArgs,
        lambda _ref: _object({}),
        _fx_rates,
    ),
)
_BY_NAME: Final = {tool.name: tool for tool in TOOLS}


def _allowed(principal: Principal, tool: Tool) -> bool:
    return all(principal.has(permission) for permission in tool.permissions)


def tool_specs(principal: Principal, reference: Reference) -> list[ToolSpec]:
    """Layer 1: the function tools offered to the model, only those the caller may use."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters(reference),
            },
        }
        for tool in TOOLS
        if _allowed(principal, tool)
    ]


# --- Running a call


class ToolExecutor:
    """Runs the model's tool calls for one caller. Never raises: every failure is a result."""

    def __init__(self, session: Session, principal: Principal, reference: Reference) -> None:
        self._session = session
        self._principal = principal
        self._reference = reference

    def execute(self, call: ToolCall) -> ToolResult:
        started = time.perf_counter()
        result = self._execute(call)
        return replace(result, duration_ms=round((time.perf_counter() - started) * 1000))

    def _execute(self, call: ToolCall) -> ToolResult:
        args = _parse(call.arguments)
        tool = _BY_NAME.get(call.name)
        if tool is None:
            return _error(call.name, "unknown_tool", f"There is no tool {call.name!r}.")
        if not _allowed(self._principal, tool):  # layer 2: before anything is fetched
            return _forbidden(call.name)
        if args is None:
            return _error(call.name, "invalid_arguments", "Arguments must be a JSON object.")
        return self._run(tool, args)

    def _run(self, tool: Tool, raw: dict[str, Any]) -> ToolResult:
        try:
            args = tool.args.model_validate(raw)
        except ValidationError as error:
            return _error(tool.name, "invalid_arguments", _message(error))
        shown = _shown_args(args)
        try:
            output = tool.run(self._session, self._principal, self._reference, args)
        except (ToolArgumentError, ProblemError) as error:
            if isinstance(error, Forbidden):
                return _forbidden(tool.name, shown)
            return _error(tool.name, "invalid_arguments", _message(error), shown)
        except Exception as error:  # a broken tool must not break the answer
            self._session.rollback()  # so the rest of the question can still write
            _logger.error("ask_tool_failed", tool=tool.name, error_type=type(error).__name__)
            return _error(tool.name, "tool_failed", "The tool failed. Try another way.", shown)
        content = json.dumps({"ok": True, "data": output.data}, separators=(",", ":"))
        amounts, numbers = _grounding(output.data)
        return ToolResult(
            name=tool.name,
            args=shown,
            ok=True,
            content=content,
            summary=output.summary,
            dashboard_link=output.dashboard_link,
            amounts=frozenset(amounts),
            numbers=frozenset(numbers),
        )


MAX_SHOWN_ARGS_CHARS: Final = 1000


def _shown_args(args: _Args) -> dict[str, Any]:
    """The validated arguments the model set, for "How I got this"; {} if oversized."""
    shown = args.model_dump(mode="json", exclude_unset=True)
    return shown if len(json.dumps(shown)) <= MAX_SHOWN_ARGS_CHARS else {}


def _parse(arguments: str) -> dict[str, Any] | None:
    """The model's arguments as a JSON object; None if they are not one."""
    try:
        value = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None  # pyright: ignore[reportUnknownVariableType]


def _message(error: ValidationError | ToolArgumentError | ProblemError) -> str:
    """What the model is told about its bad arguments."""
    if isinstance(error, ToolArgumentError):
        return str(error)
    if isinstance(error, ProblemError):
        return error.detail or error.title
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'arguments'}: {item['msg']}"
        for item in error.errors(include_url=False, include_input=False)
    )


def tool_error(code: str, message: str) -> str:
    """The content of a tool message that reports an error to the model."""
    return json.dumps({"ok": False, "error": {"code": code, "message": message}})


def _error(name: str, code: str, message: str, args: dict[str, Any] | None = None) -> ToolResult:
    return ToolResult(
        name=name,
        args=args or {},
        ok=False,
        content=tool_error(code, message),
        summary=f"Error: {message}",
        dashboard_link=None,
        amounts=frozenset(),
        numbers=frozenset(),
    )


def _forbidden(name: str, args: dict[str, Any] | None = None) -> ToolResult:
    result = _error(
        name,
        "forbidden",
        "The user's role cannot see individual pay. Offer an aggregate instead.",
        args,
    )
    return replace(result, summary="Refused: not allowed for this role")


def _is_count(key: str) -> bool:
    """Integer fields that count people, even inside an object that has a currency."""
    return key in {"n", "headcount"} or key.endswith("count") or key.startswith("employees_")


def _grounding(value: object) -> tuple[set[tuple[str, str]], set[str]]:
    """The amounts (normalised minor units, currency) and the other numbers of a tool result.

    An integer is an amount when its object has a `currency` (a Money, a Stats, a Band, a
    Comparison) and it is not a count; every other integer and decimal string is a number.
    """
    amounts: set[tuple[str, str]] = set()
    numbers: set[str] = set()

    def walk(item: object) -> None:
        if isinstance(item, dict):
            fields = cast("dict[str, object]", item)
            currency = fields.get("currency")
            for key, field_value in fields.items():
                if isinstance(field_value, int) and not isinstance(field_value, bool):
                    number = normalise_number(str(field_value))
                    if isinstance(currency, str) and not _is_count(key):
                        amounts.add((number, currency))
                    else:
                        numbers.add(number)
                elif isinstance(field_value, str):
                    if (number := _as_number(field_value)) is not None:
                        numbers.add(number)
                else:
                    walk(field_value)
        elif isinstance(item, list):
            for element in cast("list[object]", item):
                walk(element)

    walk(value)
    return amounts, numbers


def _as_number(text: str) -> str | None:
    try:
        return normalise_number(text)
    except InvalidOperation:
        return None


def normalise_number(text: str) -> str:
    """One spelling per number: `0.930` and `0.93` match, `6000000` stays as it is."""
    number = Decimal(text.strip())
    if not number.is_finite():
        raise InvalidOperation(text)
    normal = number.normalize()
    return f"{normal:f}"
