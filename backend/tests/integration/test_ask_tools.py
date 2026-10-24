"""The Ask tools and their executor (docs/10 sections 4 and 10, docs/08 section 8).

Three layers keep a caller inside their role: the tool list offered to the model, the
executor's permission re-check, and the insight services' masking and small-group rule.
"""

import json
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.modules.ask.llm import ToolCall
from salary_api.modules.ask.tools import ToolExecutor, load_reference, tool_specs
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.insights import service as insights
from tests.factories import (
    make_department,
    make_employee,
    make_fx_rates,
    make_job_role,
    make_pay_band,
    make_user,
)

AGGREGATE_TOOLS = {
    "get_pay_overview",
    "get_pay_by_group",
    "compare_groups",
    "get_pay_equity_outliers",
    "get_fx_rates",
}
INDIVIDUAL_TOOLS = {"get_top_earners", "search_employees"}


def _principal(session: Session, role: Role) -> Principal:
    user = make_user(session, role=role)
    return Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=role)


def _call(name: str, args: dict[str, Any] | str) -> ToolCall:
    arguments = args if isinstance(args, str) else json.dumps(args)
    return ToolCall(id=f"call-{name}", name=name, arguments=arguments)


def _run(session: Session, role: Role, name: str, args: dict[str, Any] | str) -> Any:
    executor = ToolExecutor(session, _principal(session, role), load_reference(session))
    return executor.execute(_call(name, args))


def _names(specs: list[dict[str, Any]]) -> set[str]:
    return {spec["function"]["name"] for spec in specs}


@pytest.fixture(autouse=True)
def _rates(db_session: Session) -> None:
    make_fx_rates(db_session)


# --- Layer 1: the tools offered to the model


def test_a_viewer_is_offered_only_aggregate_tools(db_session: Session) -> None:
    specs = tool_specs(_principal(db_session, Role.VIEWER), load_reference(db_session))

    assert _names(specs) == AGGREGATE_TOOLS
    assert "include_employees" not in json.dumps(specs)


@pytest.mark.parametrize("role", [Role.HR_MANAGER, Role.ADMIN])
def test_salary_readers_are_offered_every_tool(db_session: Session, role: Role) -> None:
    specs = tool_specs(_principal(db_session, role), load_reference(db_session))

    assert _names(specs) == AGGREGATE_TOOLS | INDIVIDUAL_TOOLS


def test_filter_values_are_enums_from_the_reference_data(db_session: Session) -> None:
    make_employee(db_session, country="DE", job_role=make_job_role(db_session, "Data Analyst"))
    make_department(db_session, "Customer Success")

    specs = tool_specs(_principal(db_session, Role.HR_MANAGER), load_reference(db_session))

    overview = next(s for s in specs if s["function"]["name"] == "get_pay_overview")
    filters = overview["function"]["parameters"]["properties"]["filters"]["properties"]
    assert filters["country"]["enum"] == ["DE"]
    assert filters["department"]["enum"] == ["Customer Success", "Engineering"]
    assert filters["job_role"]["enum"] == ["Data Analyst"]
    assert filters["level"]["enum"] == ["L1", "L2", "L3", "L4", "L5", "L6"]
    assert overview["function"]["parameters"]["additionalProperties"] is False


# --- Layer 2: the executor re-checks every call


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("get_top_earners", {"country": "DE", "n": 5}),
        ("search_employees", {"query": "Test"}),
    ],
)
def test_a_viewer_calling_an_individual_tool_is_refused_and_nothing_is_fetched(
    db_session: Session, name: str, args: dict[str, Any]
) -> None:
    make_employee(db_session, country="DE")

    result = _run(db_session, Role.VIEWER, name, args)

    assert result.ok is False
    assert json.loads(result.content)["error"]["code"] == "forbidden"
    assert "amount_minor" not in result.content
    audited = db_session.scalars(select(AuditEvent.action)).all()
    assert "insights.individuals_view" not in audited


def test_an_unknown_tool_is_a_tool_error(db_session: Session) -> None:
    result = _run(db_session, Role.ADMIN, "delete_employee", {})

    assert (result.ok, json.loads(result.content)["error"]["code"]) == (False, "unknown_tool")


@pytest.mark.parametrize(
    "args",
    [
        {"filters": {"department": "Astrology"}},
        {"filters": {"country": "XX"}},
        {"filters": {"job_role": "Wizard"}},
        {"filters": {"level": "L9"}},
        {"filters": {"country": "DE"}, "sql": "DROP TABLE employees"},
        "not json",
        "[1, 2]",
    ],
)
def test_bad_arguments_are_a_tool_error_for_the_model(
    db_session: Session, args: dict[str, Any] | str
) -> None:
    make_employee(db_session, country="DE")

    result = _run(db_session, Role.HR_MANAGER, "get_pay_overview", args)

    error = json.loads(result.content)["error"]
    assert (result.ok, error["code"]) == (False, "invalid_arguments")
    assert error["message"]


def test_an_unknown_department_names_the_value_it_did_not_know(db_session: Session) -> None:
    result = _run(
        db_session, Role.HR_MANAGER, "get_pay_overview", {"filters": {"department": "Astrology"}}
    )

    assert "Astrology" in json.loads(result.content)["error"]["message"]


def test_a_service_exception_becomes_a_tool_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("database went away")

    monkeypatch.setattr(insights, "overview", broken)

    result = _run(db_session, Role.HR_MANAGER, "get_pay_overview", {})

    assert (result.ok, json.loads(result.content)["error"]["code"]) == (False, "tool_failed")
    assert "database went away" not in result.content


# --- Layer 3: the services' masking and small-group rule hold through the tools


def test_a_small_group_is_suppressed_for_a_viewer(db_session: Session) -> None:
    for _ in range(5):
        make_employee(db_session, country="DE")
    legal = make_job_role(db_session, "Counsel", department=make_department(db_session, "Legal"))
    make_employee(db_session, country="DE", job_role=legal)
    make_employee(db_session, country="DE", job_role=legal)

    result = _run(db_session, Role.VIEWER, "get_pay_by_group", {"group_by": "department"})

    groups = {
        g["department"]["name"]: g["stats"] for g in json.loads(result.content)["data"]["groups"]
    }
    assert groups["Legal"]["suppressed"] is True
    assert groups["Legal"]["median"] is None
    assert groups["Legal"]["count"] is None


# --- What each tool returns


def test_pay_overview_returns_the_population_statistics(db_session: Session) -> None:
    for base in (5_000_000, 6_000_000, 7_000_000, 8_000_000, 9_000_000):
        make_employee(db_session, country="DE", base_minor=base)

    result = _run(db_session, Role.HR_MANAGER, "get_pay_overview", {"filters": {"country": "DE"}})

    data = json.loads(result.content)["data"]
    assert (data["currency"], data["headcount"], data["stats"]["median"]) == ("EUR", 5, 7_000_000)
    assert result.summary == "5 employees"
    assert result.dashboard_link == "/insights?country=DE"


def test_pay_by_country_groups_the_overview_by_country(db_session: Session) -> None:
    make_employee(db_session, country="DE")
    make_employee(db_session, country="FR")

    result = _run(db_session, Role.HR_MANAGER, "get_pay_by_group", {"group_by": "country"})

    data = json.loads(result.content)["data"]
    assert [group["country_code"] for group in data["groups"]] == ["DE", "FR"]


def test_pay_by_job_role_needs_a_country(db_session: Session) -> None:
    result = _run(db_session, Role.HR_MANAGER, "get_pay_by_group", {"group_by": "job_role"})

    assert json.loads(result.content)["error"]["code"] == "invalid_arguments"


def test_pay_by_job_role_lists_the_roles_of_one_country(db_session: Session) -> None:
    make_employee(db_session, country="DE", job_role=make_job_role(db_session, "Data Analyst"))

    result = _run(
        db_session,
        Role.HR_MANAGER,
        "get_pay_by_group",
        {"group_by": "job_role", "filters": {"country": "DE", "level": "L3"}},
    )

    data = json.loads(result.content)["data"]
    assert [group["job_role"]["title"] for group in data["groups"]] == ["Data Analyst"]
    assert result.dashboard_link == "/insights?country=DE&level=L3"


def test_compare_groups_returns_the_difference_computed_by_the_service(
    db_session: Session,
) -> None:
    for base in (6_000_000,) * 5:
        make_employee(db_session, country="DE", base_minor=base)
    for base in (5_000_000,) * 5:
        make_employee(db_session, country="FR", base_minor=base)

    result = _run(
        db_session,
        Role.VIEWER,
        "compare_groups",
        {"a": {"country": "DE"}, "b": {"country": "FR"}, "metric": "median"},
    )

    data = json.loads(result.content)["data"]
    assert (data["difference"], data["pct_difference"]) == (1_000_000, "0.2000")


def test_pay_equity_for_one_country_returns_the_department_rollup(db_session: Session) -> None:
    role = make_job_role(db_session)
    make_pay_band(db_session, job_role=role, country="DE", mid_minor=6_000_000)
    for _ in range(5):
        make_employee(db_session, country="DE", job_role=role, base_minor=4_000_000)

    result = _run(
        db_session, Role.VIEWER, "get_pay_equity_outliers", {"filters": {"country": "DE"}}
    )

    data = json.loads(result.content)["data"]
    assert data["groups"][0]["below_threshold"] is True
    assert data["summary"]["employees_flagged_underpaid"] == 5
    assert result.dashboard_link == "/insights/pay-equity?country=DE"


def test_pay_equity_across_countries_lists_the_most_flagged_cohorts(db_session: Session) -> None:
    role = make_job_role(db_session)
    make_pay_band(db_session, job_role=role, country="DE", mid_minor=6_000_000)
    make_pay_band(db_session, job_role=role, country="FR", mid_minor=6_000_000)
    for _ in range(5):
        make_employee(db_session, country="DE", job_role=role, base_minor=4_000_000)
        make_employee(db_session, country="FR", job_role=role, base_minor=6_000_000)

    result = _run(db_session, Role.HR_MANAGER, "get_pay_equity_outliers", {})

    data = json.loads(result.content)["data"]
    assert [cohort["country_code"] for cohort in data["flagged_cohorts"]] == ["DE"]
    assert data["cohorts_evaluated"] == 2


def test_top_earners_lists_the_highest_paid_for_a_salary_reader(db_session: Session) -> None:
    make_employee(db_session, country="DE", base_minor=9_000_000, last_name="Top")
    make_employee(db_session, country="DE", base_minor=5_000_000, last_name="Second")

    result = _run(db_session, Role.HR_MANAGER, "get_top_earners", {"country": "DE", "n": 1})

    items = json.loads(result.content)["data"]["items"]
    assert [(item["last_name"], item["amount"]["amount_minor"]) for item in items] == [
        ("Top", 9_000_000)
    ]


def test_search_employees_returns_few_fields_and_current_pay(db_session: Session) -> None:
    make_employee(db_session, country="DE", first_name="Lena", last_name="Müller")

    result = _run(db_session, Role.HR_MANAGER, "search_employees", {"query": "muller"})

    items = json.loads(result.content)["data"]["items"]
    assert len(items) == 1
    assert set(items[0]) == {
        "employee_code",
        "first_name",
        "last_name",
        "job_role",
        "level",
        "department",
        "country_code",
        "current_base",
    }
    assert result.dashboard_link == "/employees?q=muller"


def test_fx_rates_lists_the_snapshot_with_its_date(db_session: Session) -> None:
    result = _run(db_session, Role.VIEWER, "get_fx_rates", {})

    rates = json.loads(result.content)["data"]["rates"]
    assert {"currency": "EUR", "rate_to_usd": "1.085", "as_of": "2026-10-01"}.items() <= next(
        rate for rate in rates if rate["currency"] == "EUR"
    ).items()


def test_a_tool_result_lists_its_amounts_with_currency_and_its_other_numbers(
    db_session: Session,
) -> None:
    for _ in range(5):
        make_employee(db_session, country="DE", base_minor=6_000_000)

    result = _run(db_session, Role.HR_MANAGER, "get_pay_overview", {"filters": {"country": "DE"}})

    assert ("6000000", "EUR") in result.amounts
    assert "5" in result.numbers
    assert "6000000" not in result.numbers
