"""Scoring of the Ask eval set (docs/10 section 11.2). The real run needs a key; this does not."""

from pathlib import Path
from typing import Any

import pytest

from salary_api.modules.ask.schemas import AskResponse, Figure, ToolCallTrace
from scripts.eval_ask import load_cases, missing_key_message, score

EVAL_SET = Path(__file__).resolve().parents[3] / "docs" / "ai" / "evals" / "ask.yaml"


def _response(
    *,
    answer: str = "Customer Success in Germany is below band.",
    tools: list[tuple[str, dict[str, Any]]] | None = None,
    figures: list[Figure] | None = None,
    caveats: list[str] | None = None,
) -> AskResponse:
    return AskResponse(
        answer=answer,
        figures=figures or [],
        tool_calls=[
            ToolCallTrace(name=name, args=args, ok=True, summary="", duration_ms=1)
            for name, args in (tools or [])
        ],
        caveats=caveats or [],
        dashboard_link=None,
    )


def _checks(expect: dict[str, Any], response: AskResponse) -> dict[str, bool]:
    return {check.name: check.passed for check in score(expect, response)}


def test_the_eval_set_loads_and_has_policy_cases() -> None:
    cases = load_cases(EVAL_SET)

    assert len(cases) >= 5
    assert {case["role"] for case in cases} <= {"ADMIN", "HR_MANAGER", "VIEWER"}
    assert any(case["policy"] for case in cases)


def test_tool_selection_passes_when_any_expected_tool_was_called() -> None:
    response = _response(tools=[("get_pay_equity_outliers", {"filters": {"country": "DE"}})])

    checks = _checks({"tools_any_of": ["get_pay_equity_outliers", "compare_groups"]}, response)

    assert checks == {"tools": True}


def test_arguments_are_found_in_nested_filters() -> None:
    response = _response(tools=[("get_pay_equity_outliers", {"filters": {"country": "DE"}})])

    assert _checks({"args_include": {"country": "DE"}}, response) == {"args": True}
    assert _checks({"args_include": {"country": "FR"}}, response) == {"args": False}


@pytest.mark.parametrize(
    ("tools", "passed"),
    [([], True), ([("get_fx_rates", {})], False)],
)
def test_a_star_in_tools_none_of_means_no_tool_at_all(
    tools: list[tuple[str, dict[str, Any]]], passed: bool
) -> None:
    assert _checks({"tools_none_of": ["*"]}, _response(tools=tools)) == {"tools": passed}


def test_figures_must_match_within_their_tolerance() -> None:
    expect = {
        "figures": [{"label_contains": "Customer Success", "number": "0.93", "tolerance_pct": 1}]
    }
    close = Figure(label="Customer Success median compa-ratio", value=None, number="0.935")
    far = Figure(label="Customer Success median compa-ratio", value=None, number="0.90")

    assert _checks(expect, _response(figures=[close])) == {"figures": True}
    assert _checks(expect, _response(figures=[far])) == {"figures": False}


def test_answer_mentions_and_must_not_are_case_insensitive() -> None:
    response = _response(answer="I estimate customer success is low")

    checks = _checks(
        {"answer_mentions": ["Customer Success"], "must_not": ["i estimate"]}, response
    )

    assert checks == {"mentions": True, "must_not": False}


def test_caveats_must_contain_each_phrase() -> None:
    response = _response(caveats=["USD at FX as of 2026-10-01"])

    assert _checks({"caveats_contain": ["FX"]}, response) == {"caveats": True}


def test_the_run_refuses_to_start_without_a_key() -> None:
    assert "LLM_API_KEY" in (missing_key_message("") or "")
    assert missing_key_message("a-key") is None
