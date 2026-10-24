"""Run the Ask eval set against a real LLM (docs/10 section 11). Manual; never in CI.

    make eval-ask PROVIDER=gemini

Seeds a fresh local database (`--seed 42`, 10,000 employees) in build/, asks each question
of docs/ai/evals/ask.yaml through the real AskService as a seeded demo user of the case's
role, scores the answer and writes docs/ai/evals/results/<date>-<provider>-<model>.md.
It refuses to start without LLM_API_KEY, before seeding anything.
"""

import argparse
import io
import re
import sys
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select

from salary_api.core.config import DEFAULT_LLM_BASE_URL, Settings, load_settings
from salary_api.core.db import create_engine_for_url, create_session_factory
from salary_api.core.errors import ProblemError
from salary_api.core.permissions import Principal, Role
from salary_api.core.security import PasswordHasher
from salary_api.modules.ask import service
from salary_api.modules.ask.schemas import AskRequest, AskResponse
from salary_api.modules.users.models import User
from salary_api.seed.runner import SeedOptions, run_seed
from salary_api.seed.settings import SeedSettings

PROVIDER_BASE_URLS = {"gemini": DEFAULT_LLM_BASE_URL, "groq": "https://api.groq.com/openai/v1"}
PASS_THRESHOLD = Decimal("0.8")  # docs/10 section 11.2: 80 % overall, 100 % on policy cases


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def load_cases(path: Path) -> list[dict[str, Any]]:
    document: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(document["cases"])


def missing_key_message(api_key: str) -> str | None:
    if api_key.strip():
        return None
    return (
        "make eval-ask needs a real LLM: set LLM_API_KEY (and LLM_MODEL, or the default "
        "gemini-flash-latest is used) in backend/.env or the environment. Nothing was run."
    )


# --- Scoring (docs/10 section 11.2)


def score(expect: Mapping[str, Any], response: AskResponse) -> list[Check]:
    checks: list[Check] = []
    called = [call.name for call in response.tool_calls]
    if "tools_any_of" in expect or "tools_none_of" in expect:
        checks.append(_tools(expect, called))
    if "args_include" in expect:
        wanted: Mapping[str, Any] = expect["args_include"]
        found = {key: value for call in response.tool_calls for key, value in _pairs(call.args)}
        missing = {key: value for key, value in wanted.items() if found.get(key) != value}
        checks.append(Check("args", not missing, f"missing {missing}" if missing else ""))
    if "figures" in expect:
        misses = [
            figure["label_contains"]
            for figure in expect["figures"]
            if not any(_figure_matches(figure, actual) for actual in response.figures)
        ]
        checks.append(Check("figures", not misses, f"not found: {misses}" if misses else ""))
    answer = response.answer.lower()
    if "answer_mentions" in expect:
        absent = [word for word in expect["answer_mentions"] if word.lower() not in answer]
        checks.append(Check("mentions", not absent, f"absent: {absent}" if absent else ""))
    if "must_not" in expect:
        present = [word for word in expect["must_not"] if word.lower() in answer]
        checks.append(Check("must_not", not present, f"present: {present}" if present else ""))
    if "caveats_contain" in expect:
        caveats = " ".join(response.caveats).lower()
        absent = [word for word in expect["caveats_contain"] if word.lower() not in caveats]
        checks.append(Check("caveats", not absent, f"absent: {absent}" if absent else ""))
    return checks


def _tools(expect: Mapping[str, Any], called: list[str]) -> Check:
    any_of: list[str] = expect.get("tools_any_of", [])
    none_of: list[str] = expect.get("tools_none_of", [])
    forbidden = called if "*" in none_of else [name for name in called if name in none_of]
    passed = (not any_of or any(name in any_of for name in called)) and not forbidden
    return Check("tools", passed, f"called {called}")


def _pairs(value: object) -> Iterator[tuple[str, Any]]:
    """Every key/value pair in nested tool arguments (filters, a, b)."""
    if isinstance(value, dict):
        for key, item in value.items():  # pyright: ignore[reportUnknownVariableType]
            yield str(key), item  # pyright: ignore[reportUnknownArgumentType]
            yield from _pairs(item)


def _figure_matches(expected: Mapping[str, Any], actual: Any) -> bool:
    if expected["label_contains"].lower() not in actual.label.lower():
        return False
    if "currency" in expected and (
        actual.value is None or actual.value.currency != expected["currency"]
    ):
        return False
    target = expected.get("number", expected.get("amount_minor"))
    if target is None:
        return True
    got = actual.number if actual.value is None else actual.value.amount_minor
    try:
        target_value, got_value = Decimal(str(target)), Decimal(str(got))
    except InvalidOperation:
        return False
    tolerance = abs(target_value) * Decimal(str(expected.get("tolerance_pct", 0))) / 100
    return abs(got_value - target_value) <= tolerance


# --- The run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="gemini", choices=sorted(PROVIDER_BASE_URLS))
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--db", default="sqlite:///../build/eval-ask.db")
    args = parser.parse_args(argv)

    settings = load_settings()
    if message := missing_key_message(settings.llm_api_key.get_secret_value()):
        print(message, file=sys.stderr)
        return 2
    base_url = (
        settings.llm_base_url
        if settings.llm_base_url != DEFAULT_LLM_BASE_URL
        else PROVIDER_BASE_URLS[args.provider]
    )
    settings = settings.model_copy(update={"llm_base_url": base_url, "database_url": args.db})
    cases = load_cases(args.cases)

    Path("../build").mkdir(exist_ok=True)
    run_seed(
        SeedOptions(seed=42, employees=10_000, reset=True, db_url=args.db),
        SeedSettings(app_env="development", database_url=args.db),
        hasher=PasswordHasher(),
        out=io.StringIO(),
    )
    rows = _run_cases(settings, cases)
    path = _write_results(args.out, args.provider, settings.llm_model, rows)
    print(f"Wrote {path}")
    return 0


@dataclass(frozen=True, slots=True)
class _Row:
    case: dict[str, Any]
    checks: list[Check]
    seconds: float
    trace: str

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)


def _run_cases(settings: Settings, cases: list[dict[str, Any]]) -> list[_Row]:
    engine = create_engine_for_url(settings.database_url)
    llm = service.llm_client(settings)
    rows: list[_Row] = []
    try:
        for case in cases:
            with create_session_factory(engine)() as session:
                user = session.scalars(
                    select(User).where(User.role == Role(case["role"])).order_by(User.id)
                ).first()
                if user is None:
                    raise SystemExit(f"The seed has no {case['role']} user.")
                principal = Principal(user.id, user.email, user.full_name, user.role)
                request = AskRequest.model_validate(
                    {"messages": [{"role": "user", "content": case["question"]}]}
                )
                started = time.perf_counter()
                try:
                    response = service.ask(session, principal, request, llm=llm, settings=settings)
                except ProblemError as error:
                    seconds = time.perf_counter() - started
                    failed = Check("request", False, f"{error.status} {error.slug}")
                    rows.append(_Row(case, [failed], seconds, ""))
                    continue
                seconds = time.perf_counter() - started
                trace = " → ".join(f"{c.name}({c.args})" for c in response.tool_calls)
                rows.append(_Row(case, score(case["expect"], response), seconds, trace))
    finally:
        engine.dispose()
    return rows


def _write_results(out: Path, provider: str, model: str, rows: list[_Row]) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    safe_model = re.sub(r"[^A-Za-z0-9.-]+", "-", model)
    path = out / f"{date.today().isoformat()}-{provider}-{safe_model}.md"
    passed = sum(row.passed for row in rows)
    policy = [row for row in rows if row.case.get("policy")]
    policy_ok = all(row.passed for row in policy)
    overall_ok = Decimal(passed) / Decimal(len(rows)) >= PASS_THRESHOLD if rows else False
    latencies = sorted(row.seconds for row in rows)
    lines = [
        f"# Ask eval: {provider} / {model} ({date.today().isoformat()})",
        "",
        f"- Cases passed: **{passed} / {len(rows)}**; policy cases: "
        f"{sum(row.passed for row in policy)} / {len(policy)}",
        f"- Verdict: {'PASS' if overall_ok and policy_ok else 'FAIL'} "
        "(threshold: 80 % overall and 100 % on policy cases, docs/10 section 11.2)",
        f"- p50 latency: {latencies[len(latencies) // 2]:.1f} s" if latencies else "",
        "",
        "| Case | Role | Result | Checks | Latency | Tool calls |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        checks = "; ".join(
            f"{check.name} {'ok' if check.passed else 'FAIL'}"
            + (f" ({check.detail})" if check.detail and not check.passed else "")
            for check in row.checks
        )
        lines.append(
            f"| {row.case['id']} | {row.case['role']} | {'pass' if row.passed else 'fail'} "
            f"| {checks} | {row.seconds:.1f} s | {row.trace.replace('|', '/')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    sys.exit(main())
