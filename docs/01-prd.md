# Product Requirements Document — ACME Salary Management

> Defines the problem, who we are building for, what the product must do, and how we will know it works.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [02-requirements-one-pager.md](02-requirements-one-pager.md) · [03-clarifications.md](03-clarifications.md) · [05-architecture.md](05-architecture.md) · [06-data-model.md](06-data-model.md) · [08-security-rbac.md](08-security-rbac.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [11-import-export.md](11-import-export.md) · [18-implementation-plan.md](18-implementation-plan.md)

---

## 1. Problem statement

ACME's HR team manages salary data for **10,000 employees across multiple countries** in Excel spreadsheets. This is:

- **Tedious** — every edit, lookup and report is manual; there is no single source of truth.
- **Error-prone** — no validation (a salary can be typed in the wrong currency, a title can be spelled three ways), no history of who changed what.
- **Hard to analyse** — answering "how do we pay people?" (e.g. *what is the median salary for senior engineers in Germany?*, *are any teams paid below their peers?*) requires ad-hoc pivot tables, and cross-country comparisons silently mix currencies.
- **Insecure** — a spreadsheet is all-or-nothing: whoever has the file sees every salary.

We want the HR manager to **manage salary data through a web application** and **answer questions about how the organisation pays people**, reliably and safely.

## 2. Personas

| Persona | Role in system | Goals | Pain today |
|---|---|---|---|
| **Hema, HR Manager** (primary) | `HR_MANAGER` | Keep employee and salary records correct; record raises and promotions; answer leadership's pay questions quickly; spot unfair pay | Excel edits, no history, manual pivots, currency confusion |
| **Arun, HR/System Admin** | `ADMIN` | Manage user accounts and roles; maintain FX rates and country configuration; review the audit log | Shares spreadsheets by email; can't control who sees what |
| **Farah, Finance / Leadership** (read-only) | `VIEWER` | Understand payroll cost and pay distribution by country/department; never needs individual salaries | Receives full salary files she shouldn't see |

Out of scope personas: line managers (need a reporting hierarchy) and employees (self-service). See §8.

## 3. Goals and non-goals

### Goals
1. **G1 — Single source of truth** for 10,000 employees' profiles and compensation, with validated data.
2. **G2 — Full salary history** with effective dates, reasons and the person who made each change.
3. **G3 — Answer pay questions** through insights (by country, department, job title, level), a pay-equity view, and a natural-language "Ask about pay" feature.
4. **G4 — Currency-correct reporting**: per-country statistics in local currency; cross-country comparisons only in a reporting currency (USD) with the FX date shown.
5. **G5 — Least-privilege access**: role-based permissions; confidential individual salaries hidden from read-only users.
6. **G6 — Easy migration from Excel**: CSV and XLSX import with a dry-run preview, plus CSV/XLSX export.
7. **G7 — Production-quality engineering**: TDD, fast deterministic tests, CI, a live deployment at $0 cost.

### Non-goals
- Running payroll, calculating tax or deductions.
- Benefits administration, equity (RSUs), commission, overtime.
- Approval workflows, scheduled (future-dated) raises.
- Multi-tenant SaaS; SSO/MFA.

Full rationale for each exclusion: [02-requirements-one-pager.md](02-requirements-one-pager.md) and [20-trade-offs.md](20-trade-offs.md).

## 4. User stories and acceptance criteria

IDs are referenced from tests and the implementation plan ([18-implementation-plan.md](18-implementation-plan.md)).

### 4.1 Authentication and access

| ID | Story | Acceptance criteria |
|---|---|---|
| US-01 | As any user, I can log in with email and password. | Valid credentials set an httpOnly, `SameSite=Lax`, `Secure` session cookie; invalid credentials return a generic error (no user enumeration); logout clears the cookie. |
| US-02 | As an Admin, I can create users and assign one of three roles. | Only `USER_ADMIN` permission can create/modify users; role change is audited. |
| US-03 | As a Viewer, I never see individual salaries. | Salary fields are masked in list, detail and export; API omits them (not just the UI); aggregates over fewer than 5 people show "—". |
| US-04 | As any user, I only see actions I am allowed to perform. | UI hides disallowed actions; backend returns 403 regardless of UI. |

### 4.2 Employee management

| ID | Story | Acceptance criteria |
|---|---|---|
| US-10 | As an HR Manager, I can browse all employees in a paginated table. | Server-side pagination (default 25/page); total count shown; responsive < 300 ms p95 at 10k rows (see [19-performance.md](19-performance.md)). |
| US-11 | I can search by name, email or employee ID. | Case-insensitive including non-ASCII names (e.g. "müller" finds "Müller"); partial matches. |
| US-12 | I can filter by country, department, job title, level, employment type, status, currency and salary range. | Filters combine (AND); state lives in the URL so links are shareable; salary range requires a currency (or compares in USD). |
| US-13 | I can sort by name, hire date, country, salary. | Sort column restricted to an allow-list. |
| US-14 | I can create an employee. | Required fields validated; job title chosen from the controlled list; currency defaults from country; initial salary record created with reason `HIRE`; audit event written. |
| US-15 | I can edit an employee's profile. | Optimistic locking: a stale edit returns 409 with a clear message; audit diff stored. |
| US-16 | I can terminate and reactivate an employee. | Soft delete only (status + termination date); never hard-deleted; terminated employees excluded from insights by default. |

### 4.3 Salary and compensation

| ID | Story | Acceptance criteria |
|---|---|---|
| US-20 | I can record a salary change. | Requires effective date (not in the future), reason (`HIRE`, `PROMOTION`, `MERIT`, `MARKET_ADJUSTMENT`, `CORRECTION`), base amount and optional components; stores job role + level snapshot; updates the employee's current salary in the same transaction; audited. |
| US-21 | I can see an employee's salary history as a timeline. | Shows each change with date, reason, old → new, % change, level/title change, and who made it. |
| US-22 | I can record allowances and a target bonus. | Components (`ALLOWANCE`, `BONUS_TARGET`) attached to a salary record; total comp = base + allowances + bonus target. |
| US-23 | I can view amounts annually or monthly. | Stored value is annual; monthly = annual ÷ 12 as a display toggle. |
| US-24 | Amounts are always shown with their currency. | Formatting respects currency exponent (JPY has no decimals); no floating-point arithmetic. |

### 4.4 Insights and pay equity

| ID | Story | Acceptance criteria |
|---|---|---|
| US-30 | I see an org overview. | Headcount, total payroll in USD (with FX date), per-country table: count, min, max, mean, median, P25, P75 in local currency + USD equivalent. |
| US-31 | I can compare pay by department and by job title within a country. | Average and median per group; base vs total comp toggle. |
| US-32 | I can see the salary distribution for a country. | Histogram in local currency. |
| US-33 | I can see top/bottom earners per country. | HR Manager and Admin only. |
| US-34 | I can see department cost. | Total compensation per department in USD. |
| US-35 | I can analyse raises. | Average raise % and count by reason for a date range. |
| US-36 | I can see a pay-equity view. | Pay bands per job title + level + country; compa-ratio = base ÷ band midpoint; department rollup that surfaces teams systematically below band; cohort P25/median/P75; flags < 0.8 (possibly underpaid) and > 1.2 (above band); drill-down to flagged employees (names only with salary permission). |
| US-37 | Insights default to full-time employees. | Part-time and contractors excluded by default; filter overrides. |

Metric definitions: [09-insights-pay-equity.md](09-insights-pay-equity.md).

### 4.5 Import and export

| ID | Story | Acceptance criteria |
|---|---|---|
| US-40 | I can download an import template (CSV or XLSX). | Template has the documented columns and an example row. |
| US-41 | I can upload a CSV or XLSX file and see a dry-run preview before anything is saved. | Every row validated; errors listed per row and column; duplicates detected (within file and against the database, by employee code/email); nothing persisted until commit. |
| US-42 | I can commit a clean import. | All-or-nothing transaction; audit event with counts; file ≤ 4 MB. |
| US-43 | I can export the filtered employee list as CSV or XLSX. | Respects current filters and role (Viewer export has no salary columns); spreadsheet formula injection neutralised; export audited. |

Details: [11-import-export.md](11-import-export.md).

### 4.6 Ask about pay (AI)

| ID | Story | Acceptance criteria |
|---|---|---|
| US-50 | I can ask a pay question in plain English and get an answer from real data. | Answer includes key figures with currency and FX date; uses only read-only insight tools; shows "How I got this" (tools + arguments). |
| US-51 | I can ask follow-up questions. | Last ~6 turns sent with each request; history not stored server-side. |
| US-52 | The AI respects my role. | A Viewer asking for individual salaries gets an access message; tools not permitted for the role are never offered to the model. |
| US-53 | The feature degrades gracefully. | Hidden/disabled when no API key is configured; rate-limit errors show "busy, retry in X s". |

Details: [10-ai-ask-design.md](10-ai-ask-design.md).

### 4.7 Administration

| ID | Story | Acceptance criteria |
|---|---|---|
| US-60 | As an Admin, I can maintain FX rates. | Rate to USD (decimal), as-of date, source; changes audited. |
| US-61 | As an Admin, I can maintain country configuration. | Code, name, default currency. |
| US-62 | As an Admin, I can view the audit log. | Filter by actor, action, entity, date; shows diffs. |

## 5. Functional requirements summary

| Area | Requirement |
|---|---|
| Data | Employee profile, controlled job roles and departments, salary records (append-only), salary components, FX rates, countries, users, audit events, import jobs. Schema: [06-data-model.md](06-data-model.md). |
| API | REST under `/api/v1`, OpenAPI-documented, RFC 9457 problem+json errors. Spec: [07-api-spec.md](07-api-spec.md). |
| UI | Login, employees list/detail/new/import, insights, pay-equity, ask, admin (users, FX, countries, audit). Screens: [13-frontend-ux.md](13-frontend-ux.md). |
| Seed | Deterministic script producing 10,000 employees across 10 countries with realistic history. See [12-seed-data.md](12-seed-data.md). |

## 6. Non-functional requirements

| Category | Requirement |
|---|---|
| **Performance** | Employee list and insight endpoints p95 < 300 ms at 10k employees (server time, warm). Seed of 10k employees < 5 s locally. Budgets: [19-performance.md](19-performance.md). |
| **Correctness** | Money stored as integer minor units with ISO 4217 currency; no floats; statistics identical across SQLite and Postgres. |
| **Security** | Argon2 password hashing; JWT in httpOnly cookie; permission checks on every endpoint; masking + small-group rule; audit of all mutations, imports, exports and admin actions; secrets only via environment. See [08-security-rbac.md](08-security-rbac.md). |
| **Privacy** | Data minimisation — no DOB, gender, address, bank details. LLM receives aggregates by default. |
| **Reliability** | Soft deletes; optimistic locking; all-or-nothing imports; Turso point-in-time restore for recovery. |
| **Usability** | Responsive layout; keyboard-friendly; WCAG AA contrast; clear validation messages; currency always labelled. |
| **Maintainability** | Layered backend (router → service → repository), pure domain module, typed end-to-end (Pyright strict, TS strict, generated API client). |
| **Testability** | TDD; fast, deterministic tests (in-memory SQLite, frozen time, seeded randomness); coverage ≥ 90 % on domain + services. See [14-testing-strategy.md](14-testing-strategy.md). |
| **Cost** | $0 hosting: Vercel (web + API) + Turso; free LLM tier. See [17-deployment.md](17-deployment.md). |
| **Portability** | Database switchable by `DATABASE_URL` only; proven by a Postgres CI job. |

## 7. Success metrics

| Metric | Target |
|---|---|
| HR can answer "median salary for X in country Y" | < 30 seconds via insights or Ask |
| Data import of a 10k-row Excel file | Dry-run report < 10 s; zero partial imports |
| Viewer data leakage | 0 individual salaries exposed (tested in the authz matrix) |
| Test suite | Backend unit + integration < 60 s locally; deterministic (no flaky reruns) |
| Ask eval set | ≥ 80 % of eval questions answered with correct tool and figures (**TBD** — threshold to confirm after the first eval run) |
| Deployed demo | Available throughout review; cold start ≈ 1–2 s |

## 8. Scope boundaries

**In scope** and **out of scope** lists are maintained in [02-requirements-one-pager.md](02-requirements-one-pager.md). Key exclusions: payroll/tax, equity/commission/benefits, line-manager and self-service roles, future-dated raises, approvals, SSO/MFA, multi-tenancy, live FX feeds, gender/demographic pay-gap analysis, custom backup system.

## 9. Assumptions

Each assumption has a matching question in [03-clarifications.md](03-clarifications.md).

1. Salaries are annual base pay in the employee's local currency; HR thinks in annual figures.
2. A single reporting currency (USD) is acceptable for cross-country views, using a static, admin-maintained FX table.
3. The HR manager wants pay analytics (distribution, equity), not payroll processing.
4. Three roles (Admin, HR Manager, Viewer) are sufficient for the assessment.
5. Synthetic seeded data is acceptable for the deployed demo; demo credentials can be shared with reviewers.
6. A free LLM tier is acceptable for the demo because the data is synthetic.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Turso Python SQLAlchemy driver is young (original repo archived June 2025) | Deploy blocked | Day-1 deploy spike; fallback to Neon Postgres by changing `DATABASE_URL` ([adr/0002-sqlite-everywhere-turso.md](adr/0002-sqlite-everywhere-turso.md)) |
| Free LLM tier limits (requests/tokens per minute) | Ask feature slow/unavailable in demo | Compact prompts, 4-step cap, friendly 429 handling, Groq fallback |
| Gemini free tier may train on prompts | Privacy concern | Synthetic data only; documented; aggregates by default; paid/no-training tier required for real use |
| Scope creep (many features) | Quality drops | Milestone order puts core first; AI last; check-in after each milestone |
| Serverless limits (4.5 MB body, stateless) | Import/export failures | File cap 4 MB; dry-run stored in `import_jobs` |
| Reviewer opens demo weeks later | Dead link | $0 always-on hosting with no trial expiry |
