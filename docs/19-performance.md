# 19 — Performance

> Performance budgets, why the design meets them at 10,000 employees, how we will measure them, and the scaling path if the data grows.

**Status:** Budgets are **targets**; local measurements are in §9, deployed numbers are pending · **Last updated:** 2026-10-24
**Related:** [05-architecture.md](05-architecture.md) · [06-data-model.md](06-data-model.md) · [07-api-spec.md](07-api-spec.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [12-seed-data.md](12-seed-data.md) · [17-deployment.md](17-deployment.md) · [18-implementation-plan.md](18-implementation-plan.md) · ADRs [0002](adr/0002-sqlite-everywhere-turso.md), [0003](adr/0003-sync-sqlalchemy-serverless.md), [0007](adr/0007-pure-python-stats.md), [0016](adr/0016-deploy-vercel-turso.md)

---

## 1. Philosophy

The problem is small: **10,000 employees, about 24,000 salary records, about 10 MB of data.** At this scale the main performance risks are not algorithmic. They are **network round-trips** (serverless function ↔ Turso), **cold starts**, and **accidental N+1 queries**. The design keeps the system simple (no cache layer, no queues, no materialized views) and spends effort on:

1. Few queries per request (one list query + one count; one aggregate query per insight).
2. The right indexes for every filter and sort.
3. Doing statistics in pure Python over compact integer lists ([ADR 0007](adr/0007-pure-python-stats.md)).
4. Keeping the API function and the database in the same region.
5. Measuring instead of guessing, with results committed in this document.

---

## 2. Budgets (targets)

| Operation | Target | Environment | Notes |
|---|---|---|---|
| Seed 10,000 employees (+ ~24k salary records, ~40k components) | **< 5 s** | Local SQLite file, laptop | Bulk Core `insert()` in chunks of 1,000 |
| Load seed into Turso | **< 60 s** **(proposed)** | `turso db create --from-file` | Avoids remote row-by-row inserts entirely |
| `GET /employees` (list, any filter/sort, page 25) | **p95 < 300 ms** | Deployed, warm function | Measured server-side (handler time) and end-to-end |
| `GET /employees/{id}` | **p95 < 300 ms** | Deployed, warm | |
| Insight endpoints (overview, by-department, by-job-title, distribution, department-cost, raises, pay-equity) | **p95 < 300 ms** | Deployed, warm | Whole-org population, the worst case |
| Salary change / create / update | **p95 < 300 ms** | Deployed, warm | One transaction, a few statements |
| Export 10,000 rows (CSV / XLSX) | **< 3 s** CSV / **< 5 s** XLSX | Deployed | ~1.4 MB CSV / ~600 KB XLSX, under the 4.5 MB body cap. XLSX is set at 5 s because openpyxl alone takes about 2.5 s to write 190,000 cells (measured, §9) |
| Import dry-run of 10,000 rows | **< 5 s** **(proposed)** | Deployed | Validation in memory; 2 duplicate-check queries |
| Import commit of 10,000 rows | **< 30 s** **(proposed)** | Deployed | One transaction, chunked inserts with IDs pre-allocated in Python; checked against the day-1 spike's bulk-insert timing, and the row cap is lowered if needed |
| Cold start (first request after idle) | **~1–2 s** | Vercel Python function | Not part of the p95 budget; measured and reported separately |
| Ask about pay | **< 15 s** typical **(proposed)** | Deployed, LLM-dependent | Dominated by LLM latency (up to 4 tool steps). Shows a spinner; not part of the p95 budget |
| Frontend: Largest Contentful Paint on `/employees` | **< 2.5 s** **(proposed)** | Deployed, warm, desktop | Server-rendered first page |
| Local test suite (backend unit + integration) | **< 30 s** **(proposed)** | Laptop, pytest-xdist | Fast feedback for TDD |

"Warm" means the function instance is already running. p95 is computed over at least 100 requests per endpoint.

---

## 3. Scale math: why 10k is comfortably small

| Quantity | Estimate |
|---|---|
| Employee rows | 10,000 × ~250 bytes ≈ **2.5 MB** |
| Salary records | ~30,000 × ~100 bytes ≈ **3 MB** |
| Salary components | ~40,000 × ~50 bytes ≈ **2 MB** |
| Total with indexes | **≈ 10 MB** |
| Whole-org insight input | 10,000 integers (8 bytes each in SQLite; ~28 bytes as Python ints) ≈ **< 1 MB in memory** |
| Sorting 10,000 ints in Python | **≈ 1 ms** |
| Percentiles over sorted lists for ~100 groups | **< 5 ms** total |
| Biggest single response (list page) | 25 rows ≈ **10 KB** JSON |
| Export | 10,000 rows ≈ **1 MB** CSV |

The whole working set fits in SQLite's page cache. Query time is dominated by the number of round-trips, not by data volume.

---

## 4. Query approach

### 4.1 Employee list

One page query and one count query:

```sql
SELECT e.*, jr.title, d.name AS department
FROM employees e
JOIN job_roles jr ON jr.id = e.job_role_id
JOIN departments d ON d.id = jr.department_id
WHERE e.status = :status
  AND e.country_code IN (:countries)
  AND e.search_text LIKE :term ESCAPE '\'
ORDER BY e.last_name, e.first_name, e.id
LIMIT :page_size OFFSET :offset;

SELECT count(*) FROM employees e JOIN ... WHERE <same filters>;
```

- Joins to small reference tables are cheap (35 job roles, 9 departments).
- **No N+1:** role and department come from the join, not lazy loads. A test with SQLAlchemy query counting asserts "≤ 3 queries" for the list endpoint (loading the current user, the page, the count) ([14-testing-strategy.md](14-testing-strategy.md)).
- **Offset pagination** is fine: the deepest page (400 × 25) still scans at most 10k index entries. Keyset pagination is the documented upgrade path (§7).
- **Search:** `search_text LIKE '%term%'` can't use a B-tree index, so it scans at most 10k short strings: about 3 ms for the page and its count (measured, SQLite in memory, 10k rows). There is no `search_text` index: SQLite would not use it even for a prefix `LIKE` (case-insensitive by default), so it would only cost writes. FTS5 is the upgrade path if search ever slows down.

### 4.2 Insights

```sql
-- one query per insight, returning the minimal columns needed, pre-sorted
SELECT e.country_code, e.current_base_minor
FROM employees e
WHERE e.status = 'ACTIVE' AND e.employment_type = 'FULL_TIME'
ORDER BY e.country_code, e.current_base_minor;
```

- The database does filtering, grouping keys and sorting. Python (`domain/stats.py`) computes count, min, max, mean, median, P25 and P75 per group in one pass over each sorted list.
- Portable: percentiles use linear interpolation in Python, which gives the same numbers as Postgres `PERCENTILE_CONT` without depending on it (SQLite lacks it). Results are identical on SQLite, libSQL and Postgres ([ADR 0007](adr/0007-pure-python-stats.md)).
- USD views convert per row in Python using the cached-per-request FX table (≤ 10 rows).
- Pay-equity groups by `(job_role_id, level, country_code)`, about 1,360 possible cohorts (the seeded bands), typically a few hundred non-empty. Still one query and in-memory grouping.
- `raises` reads `salary_records` filtered by `effective_date` range (indexed) and pairs each record with the previous one for the same employee using a window function (`LAG`), supported by SQLite ≥ 3.25 and Postgres; or ordered rows and pairing in Python **(implementation choice at milestone 7)**.

### 4.3 Writes

- A salary change is about five statements in one transaction: insert record, insert components (executemany), update employee (with version check), insert audit event, commit.
- Import commit uses Core `insert()` with lists of dicts, in chunks of 1,000, inside one transaction.

---

## 5. Indexes

Defined in [06-data-model.md](06-data-model.md); listed here with the query each serves.

| Index | Serves |
|---|---|
| `uq_employees_employee_code` | Lookup by code, import duplicate check |
| `uq_employees_email` | Import duplicate check |
| `ix_employees_country_status` | Country filter; per-country insights |
| `ix_employees_job_role_level` | Designation/level filters; pay-equity cohorts |
| `ix_employees_status_employment_type` | Default insight population (ACTIVE + FULL_TIME) |
| `ix_employees_currency_base` | Salary range filter within one currency; top/bottom earners |
| `ix_employees_last_first` | Default list sort |
| `ix_salary_records_employee_effective` | Salary timeline; current-record lookup |
| `ix_salary_records_effective_reason` | Raise statistics by period |
| `ix_salary_components_record` | Components for a record |
| `ix_audit_events_actor_action_at` | Ask rate limit; login failure limit |
| `ix_audit_events_at` | Admin audit log, newest first |

Rule: every filter and sort exposed by the API must have a supporting index, or a note here explaining why a scan is acceptable. Scans accepted at 10k rows (each well under the list budget): infix search (`LIKE '%term%'`), sorts by `first_name`, `hire_date`, `level` or `current_total`, a `comp=total` salary range, and a `salary_basis=usd` range or sort (an `OR` of one range per currency, or a `CASE` key). `employee_code` sorts use `uq_employees_employee_code`; a range on `current_base` within one currency uses `ix_employees_currency_base`. `EXPLAIN QUERY PLAN` output for the main queries is captured in this doc during milestone 7.

---

## 6. Serverless and network factors

### 6.1 Turso latency and region

- Every query is a network round-trip from the Vercel function to Turso. At about 1–5 ms per round-trip in the same region, and about 2–4 queries per request, the network adds about 10–20 ms. Across regions (e.g. a US function talking to an EU database) it could add 100+ ms per query and blow the budget.
- **Decision:** deploy the Vercel API function and the Turso database in the **same region**: **US-East by default, Mumbai as the alternative** ([ADR 0003](adr/0003-sync-sqlalchemy-serverless.md), [17-deployment.md](17-deployment.md)). The deploy spike confirms both services are available in the chosen region.
- Keep per-request query counts low (§4); an N+1 bug costs far more remotely than locally.

### 6.2 Connections

- `NullPool` in serverless mode: no pool held across invocations, one connection per request.
- Local development and tests use a normal pool (or `StaticPool` for in-memory tests).

### 6.3 Cold starts

- Expected about 1–2 s on Vercel Python functions (versus about 50 s on Render's free tier, a reason for the hosting choice, [ADR 0016](adr/0016-deploy-vercel-turso.md)).
- Mitigations: keep module-level imports lean (e.g. import `openpyxl` and the LLM SDK lazily inside the modules that need them); avoid work at import time; no ORM metadata reflection at startup.
- Cold-start time is measured separately and reported with the p95 numbers; it is not hidden inside them.

### 6.4 Payload limits

Vercel caps request and response bodies at 4.5 MB. All responses are designed to stay well below it (largest: about 1 MB export). Import uploads are capped at 4 MB.

---

## 7. Scaling path (if ACME grows beyond 10k)

None of these are built now. They are the documented next steps, in the order we'd apply them.

| Trigger | Step | Effort |
|---|---|---|
| Search noticeably slow (≫ 100k employees) | SQLite **FTS5** virtual table (or `pg_trgm` on Postgres) for `search_text` | Small |
| Deep pagination slow | **Keyset pagination** (`WHERE (last_name, first_name, id) > (...)`) | Small |
| Insight queries slow (≥ ~1M employees) | Move percentiles into the DB: **`PERCENTILE_CONT`** on Postgres (switch via `DATABASE_URL`, already CI-tested on Postgres 17). Same interpolation method, so the numbers don't change | Medium |
| Insights recomputed too often | **Materialized summary tables** per (country, department, role, level), refreshed on write or on a schedule; or Postgres materialized views | Medium |
| Read-heavy dashboards with many concurrent users | **HTTP caching** of insight responses (short TTL, `Cache-Control: private`, keyed by user permissions), or a per-request memo of the FX table and reference data | Small–medium |
| Many concurrent writers | Postgres (SQLite serializes writes); Turso's concurrent writes are an option to evaluate | Medium |
| Large imports (≫ 10k rows or > 4 MB) | Direct-to-storage upload + background job (queue) instead of an in-request import | Large |
| Global user base | Read replicas (Turso embedded replicas or Postgres read replicas) near users | Medium |

The trigger thresholds are estimates; the decision to act would come from measurements in this document.

---

## 8. Measurement plan

| What | How | When | Where results go |
|---|---|---|---|
| Seed time | `make seed` prints elapsed time per phase (users, migrate, generate, insert) and the total | Milestone 6 | §9 |
| Query plans | `EXPLAIN QUERY PLAN` for list (each filter), each insight | Milestone 7 | §9 |
| N+1 guard | pytest asserting query count per endpoint | Milestones 4–7 (permanent tests) | CI |
| API latency (local) | `backend/scripts/measure_perf.py` hitting each main endpoint 30× (`-n` to change) with the 10k seed, reporting p50/p95 | B10 | §9.1 |
| API latency (deployed) | Same script against the Vercel URL (warm), plus 10 cold-start samples | Milestone 14 | §9 |
| Frontend | Lighthouse (desktop) on `/employees` and `/insights` | Milestone 14 | §9 |
| Test suite time | pytest `--durations=10` in CI | Ongoing | CI logs |

Benchmarks are read-only and never run against production data other than the seeded demo.

---

## 9. Results

Measured values; each row records the date, block and environment. TBD rows need the deployment.

| Metric | Target | Measured | Date / commit | Environment |
|---|---|---|---|---|
| Seed 10k (local) | < 5 s | B10 recheck: **3.75–3.80 s** with `make seed` (users 0.4–0.5 s, generate 1.5–1.6 s, insert 1.6–1.7 s) at load ≈ 4–7. Earlier: **3.2–3.4 s** with `make seed` (users 0.5–0.65 s of argon2, migrate < 0.1 s, generate 1.0–1.1 s, insert incl. reset 1.6–1.7 s); first build 2.9 s; **2.3 s** in memory (the golden test) | 2026-10-24 / after the B5 review | Linux, 4 vCPU shared with other jobs (load ≈ 4.5), Python 3.13, SQLite WAL |
| Turso load | < 60 s | TBD | | |
| `GET /employees` p95 | < 300 ms | **41–55 ms** (default, search, USD salary sort) | 2026-10-24, B10 | Local uvicorn on the 10k seed (§9.1); deployed TBD |
| `GET /insights/overview` p95 | < 300 ms | **201–272 ms** | 2026-10-24, B10 | Same |
| `GET /insights/pay-equity` p95 | < 300 ms | cohorts **496–527 ms (over)**; departments 53–74 ms | 2026-10-24, B10 | Same |
| Salary change p95 | < 300 ms | **34–36 ms** | 2026-10-24, B10 | Same |
| Export 10k CSV / XLSX | < 3 s / < 5 s | 0.7–0.9 s / 3.3–4.0 s | 2026-10-24, B7 | Local: 4-core dev container, Python 3.13, in-memory SQLite (`RUN_SLOW=1 uv run pytest -m slow -n 0 -s tests/integration/test_import_timing.py`) |
| Import dry-run / commit 10k | < 5 s / < 30 s | CSV 0.6–1.2 s, XLSX 3.6 s / 1.3–2.1 s | 2026-10-24, B7 | Same; 1.37 MB CSV, 0.49 MB XLSX, every row with a bonus and an allowance. Turso not measured yet |
| Cold start | ~1–2 s | TBD | | |
| LCP `/employees` | < 2.5 s | TBD | | |
| Backend test suite | < 30 s | 73–143 s for 1,270 tests with coverage (over) | 2026-10-24, B10 | `make test-backend`, pytest-xdist, 4 vCPU at load ≈ 7–13 from other jobs |

### 9.1 API latency on the 10k seed (local, B10)

Measured on 2026-10-24 with [`backend/scripts/measure_perf.py`](../backend/scripts/measure_perf.py)
(httpx, one client, sequential): 2 warm-up requests, then 30 timed requests per endpoint, timed end
to end on the client (request sent to body read). The API ran under `uvicorn` (one worker,
`LOG_LEVEL=WARNING`) on a scratch SQLite file seeded with `--seed 42 --employees 10000`, signed in
as the HR manager (no masking: the full-cost path). Machine: Linux container, **4 vCPU shared with
other jobs** (load average 3–8 during the runs), Python 3.13. Two runs; each cell is the range
over both. To rerun, follow the script's docstring.

| Endpoint | p50 (ms) | p95 (ms) | Budget |
|---|---|---|---|
| `POST /auth/login` (argon2 verify) | 258–273 | 323–395 | none set |
| `GET /employees` (default page of 25) | 28–30 | 41–45 | p95 < 300 ms |
| `GET /employees?q=smith` | 19–28 | 41–42 | p95 < 300 ms |
| `GET /employees?sort=-current_base&salary_basis=usd` | 29–40 | 51–55 | p95 < 300 ms |
| `GET /employees/{id}` | 11–13 | 19–24 | p95 < 300 ms |
| `GET /employees/{id}/salary-history` | 13–17 | 19–22 | p95 < 300 ms |
| `POST /employees/{id}/salary-changes` | 19–24 | 34–36 | p95 < 300 ms |
| `GET /insights/overview` | 109–131 | 201–272 | p95 < 300 ms |
| `GET /insights/by-department` | 73–91 | 148–161 | p95 < 300 ms |
| `GET /insights/pay-equity` (cohorts, whole org) | 293–347 | **496–527** | p95 < 300 ms |
| `GET /insights/pay-equity?view=departments&country=DE` | 38–40 | 53–74 | p95 < 300 ms |
| `GET /employees/export?format=csv` (all 9,700 active) | 967–1,074 | 1,214–1,451 | < 3 s |
| `POST /imports` (dry-run of a 10,000-row, 1.51 MB CSV) | 1,399–1,465 | 1,894–1,944 | < 5 s |

Every endpoint is inside its budget except the whole-org pay-equity cohorts view, which returns
all 1,175 cohorts (about 500 KB of JSON) in one response and is about 1.7× over; paging the
cohorts or loading the summary first is the fix. These are local numbers on a busy machine: the
deployed (Vercel + Turso) numbers and the cold start are still to be measured (§8).
