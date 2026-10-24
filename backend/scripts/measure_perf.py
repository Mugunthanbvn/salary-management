"""Measure p50/p95 latency of the main API endpoints against a running server.

For docs/19-performance.md section 9. Seed a scratch database and start the API on it first,
so the salary changes and import jobs this script writes never touch backend/dev.db:

    cd backend
    uv run python -m salary_api.seed --seed 42 --employees 10000 --reset \
        --db-url sqlite:////tmp/perf.db
    DATABASE_URL=sqlite:////tmp/perf.db LOG_LEVEL=WARNING \
        uv run uvicorn salary_api.main:app --port 8765
    # in another shell
    uv run python scripts/measure_perf.py --base-url http://127.0.0.1:8765 -n 30

It signs in as the seeded HR manager. The password comes from SEED_HR_PASSWORD, or else the
development default in backend/.env.example (never from .env). Times are end-to-end on the
client (request sent to body read), so they include HTTP and JSON work, not only the handler.
"""

import argparse
import csv
import io
import math
import os
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"
HR_EMAIL = "hr@acme.example"
IMPORT_ROWS = 10_000
WARM_UP = 2  # requests per endpoint that are sent but not timed


@dataclass(frozen=True)
class Result:
    name: str
    samples: list[float]  # seconds

    @property
    def p50_ms(self) -> float:
        return statistics.median(self.samples) * 1000

    @property
    def p95_ms(self) -> float:
        return percentile(self.samples, 95) * 1000


def percentile(samples: list[float], pct: float) -> float:
    """Nearest-rank percentile: the smallest sample with at least pct % of samples at or below."""
    ordered = sorted(samples)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def env_example_value(name: str) -> str:
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip()
    raise SystemExit(f"{name} is not set and not in {ENV_EXAMPLE}")


def timed(name: str, n: int, send: Callable[[int], httpx.Response], expected: int = 200) -> Result:
    """Send n + WARM_UP requests; `send(i)` gets the request number, for unique payloads."""
    samples: list[float] = []
    for i in range(n + WARM_UP):
        started = time.perf_counter()
        response = send(i)
        _ = response.content
        elapsed = time.perf_counter() - started
        if response.status_code != expected:
            raise SystemExit(f"{name}: HTTP {response.status_code} {response.text[:300]}")
        if i >= WARM_UP:
            samples.append(elapsed)
    return Result(name, samples)


def import_csv(template: str, rows: int) -> bytes:
    """The template's example row repeated with unique codes and emails (no clash with seed)."""
    reader = csv.DictReader(io.StringIO(template.lstrip("﻿")))
    example = next(reader)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(reader.fieldnames or []))
    writer.writeheader()
    for n in range(1, rows + 1):
        writer.writerow(
            example | {"employee_code": f"ACME-{900000 + n:06d}", "email": f"perf.{n}@acme.example"}
        )
    return out.getvalue().encode("utf-8")


def measure(client: httpx.Client, n: int, password: str) -> list[Result]:
    login = {"email": HR_EMAIL, "password": password}
    results = [timed("POST /auth/login", n, lambda _: client.post("/auth/login", json=login))]
    client.post("/auth/login", json=login).raise_for_status()  # keep the session cookie

    page = client.get("/employees", params={"page": 2, "page_size": n + WARM_UP}).json()
    targets: list[dict[str, Any]] = page["items"]
    first_id = targets[0]["id"]
    today = datetime.now(UTC).date().isoformat()

    def salary_change(i: int) -> httpx.Response:
        employee = targets[i]
        base = employee["current_base"]
        body = {
            "version": employee["version"],
            "effective_date": today,
            "reason": "MERIT",
            "base_minor": int(base["amount_minor"]) + 100_000,
            "components": [],
        }
        return client.post(f"/employees/{employee['id']}/salary-changes", json=body)

    get = client.get
    results += [
        timed("GET /employees (default)", n, lambda _: get("/employees")),
        timed("GET /employees?q=", n, lambda _: get("/employees", params={"q": "smith"})),
        timed(
            "GET /employees?sort=-current_base (USD)",
            n,
            lambda _: get("/employees", params={"sort": "-current_base", "salary_basis": "usd"}),
        ),
        timed("GET /employees/{id}", n, lambda _: get(f"/employees/{first_id}")),
        timed(
            "GET /employees/{id}/salary-history",
            n,
            lambda _: get(f"/employees/{first_id}/salary-history"),
        ),
        timed("POST /employees/{id}/salary-changes", n, salary_change, expected=201),
        timed("GET /insights/overview", n, lambda _: get("/insights/overview")),
        timed("GET /insights/by-department", n, lambda _: get("/insights/by-department")),
        timed("GET /insights/pay-equity (cohorts)", n, lambda _: get("/insights/pay-equity")),
        timed(
            "GET /insights/pay-equity (departments, DE)",
            n,
            lambda _: get("/insights/pay-equity", params={"view": "departments", "country": "DE"}),
        ),
        timed(
            "GET /employees/export (CSV, all)",
            n,
            lambda _: get("/employees/export", params={"format": "csv"}),
        ),
    ]

    upload = import_csv(get("/imports/template").text, IMPORT_ROWS)
    print(f"import file: {IMPORT_ROWS:,} rows, {len(upload) / 1e6:.2f} MB", file=sys.stderr)
    files = {"file": ("perf.csv", upload, "text/csv")}
    results.append(
        timed(
            "POST /imports (dry-run, 10k CSV)",
            n,
            lambda _: client.post("/imports", files=files),
            expected=201,
        )
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure p50/p95 latency of the main API endpoints."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("-n", type=int, default=30, help="timed requests per endpoint")
    args = parser.parse_args()
    password = os.environ.get("SEED_HR_PASSWORD") or env_example_value("SEED_HR_PASSWORD")

    with httpx.Client(base_url=f"{args.base_url}/api/v1", timeout=60) as client:
        results = measure(client, args.n, password)

    print("| Endpoint | n | p50 (ms) | p95 (ms) |\n|---|---|---|---|")
    for result in results:
        row = [f"`{result.name}`", str(len(result.samples))]
        print("| " + " | ".join([*row, f"{result.p50_ms:.0f}", f"{result.p95_ms:.0f}"]) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
