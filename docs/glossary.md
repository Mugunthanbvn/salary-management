# Glossary of canonical names and values

> One place for every name, enum and number that more than one doc uses. **If a doc disagrees with this file, this file wins**, and the doc is a bug to fix. Code and tests use exactly these spellings.

- **Status:** Accepted
- **Last updated:** 2026-10-24
- **Related:** [README](README.md) (v1 scope) · [06-data-model.md](06-data-model.md) · [07-api-spec.md](07-api-spec.md) · [08-security-rbac.md](08-security-rbac.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [11-import-export.md](11-import-export.md)

---

## 1. Roles and permissions

| Kind | Values |
|---|---|
| Roles | `ADMIN`, `HR_MANAGER`, `VIEWER` |
| Permissions | `EMPLOYEE_READ`, `EMPLOYEE_WRITE`, `SALARY_READ`, `SALARY_WRITE`, `INSIGHTS_READ`, `EXPORT`, `IMPORT`, `ASK`, `USER_ADMIN`, `FX_ADMIN`, `REFERENCE_ADMIN`, `AUDIT_READ` |

Role → permission matrix: [08-security-rbac.md](08-security-rbac.md) §3.1. Code checks permissions, never role names.

## 2. Domain enums

| Field | Values |
|---|---|
| `level` | `L1` Associate · `L2` Mid · `L3` Senior · `L4` Lead/Staff · `L5` Principal · `L6` Director |
| `employment_type` | `FULL_TIME`, `PART_TIME`, `CONTRACTOR` |
| `status` (employee) | `ACTIVE`, `TERMINATED` |
| `reason` (salary record) | `HIRE`, `PROMOTION`, `MERIT`, `MARKET_ADJUSTMENT`, `CORRECTION` |
| `type` (salary component) | `ALLOWANCE`, `BONUS_TARGET` |
| `status` (import job) | `DRY_RUN`, `COMMITTED`, `FAILED`, `EXPIRED` |
| `format` (import job) | `CSV`, `XLSX` (uppercase in the DB and the API) |
| Pay-equity flag | `UNDERPAID` (< 0.80), `IN_BAND` (0.80–1.20 inclusive), `OVERPAID` (> 1.20) |

## 3. Numbers and rules

| Name | Value | Notes |
|---|---|---|
| `MIN_GROUP_SIZE` | **5** | Callers without `SALARY_READ` get `suppressed: true` for any group with fewer than 5 people. All values **and `count`** are `null` |
| `PAY_EQUITY_LOW` / `PAY_EQUITY_HIGH` | `0.80` / `1.20` | Compared on the unrounded ratio; boundaries are `IN_BAND` |
| Department rollup threshold | median compa-ratio **< 0.95** → `below_threshold: true` | |
| Band width (seed) | `min = 0.8 × mid`, `max = 1.2 × mid` | |
| Rounding | **half-even**, everywhere (means, percentiles, FX conversion, monthly display) | |
| Percentile method | linear interpolation between closest ranks (= NumPy `linear`, SQL `PERCENTILE_CONT`) | |
| Salary currency | always the employee's country `default_currency` | A country change is a salary change |
| Page size | default `25`, max `100` | |
| Responsive | Fully mobile responsive from **360 px**; breakpoints `< 640` phone, `640–1023` tablet, `≥ 1024` desktop; design checks at 390 × 844 and 1440 × 900; touch targets ≥ 44 px | [13](13-frontend-ux.md) §8 |
| JWT lifetime | 8 h (`JWT_TTL_MINUTES=480`) | |
| Login failure limit | 5 failures per email in 15 min → `429` for 15 min | Counted from `auth.login_failed` |
| Ask rate limit | 20 per user per hour (`ASK_RATE_LIMIT_PER_HOUR`) | Counted from `ask.query` |
| Ask limits | message ≤ **1,000** chars, ≤ 6 turns, ≤ 4 tool steps | Same cap in the API and the UI |
| Upload cap | 4 MB | |
| Import row cap | 10,000, lowered if the spike's bulk-insert timing says so | |
| Dry-run expiry | 24 h | |
| Seed | `--seed 42`, anchor date `2026-10-01`, FX `as_of` `2026-10-01` | |
| Job roles | 35 roles; one pay band per role × allowed level × country (≈ 1,360 bands) | Seeded |

## 4. Audit actions

Dotted, lowercase, `<entity>.<verb>`. The rate limiters count these exact strings.

| Action | Written when | v1? |
|---|---|---|
| `auth.login` | successful login | ✅ |
| `auth.login_failed` | failed login (`entity = "auth"`, `diff.email_hash`) | ✅ |
| `auth.logout` | logout | ✅ |
| `employee.create` | employee created (with its `HIRE` record) | ✅ |
| `employee.update` | profile edited | ✅ |
| `employee.terminate` / `employee.reactivate` | status change | ✅ |
| `salary.change` | salary change recorded | ✅ |
| `import.dry_run` | upload validated | ✅ |
| `import.commit` | import committed | ✅ |
| `import.fail` | commit rolled back | ✅ |
| `export.download` | export generated | ✅ |
| `insights.individuals_view` | top earners or pay-equity cohort drill-down viewed | ✅ |
| `ask.query` | Ask question answered or failed | ✅ (if Ask is built) |
| `fx.update`, `reference.country.update`, `user.create`, `user.update` | admin actions | cut from v1 |

## 5. Errors (RFC 9457 problem+json)

`type` = `https://acme.example/problems/<slug>`. Slugs are kebab-case.

| Status | Slug | When |
|---|---|---|
| 400 | `bad-request` | Unreadable upload, or a header row that doesn't match the template |
| 401 | `unauthenticated` | Missing, invalid or expired token; inactive user |
| 403 | `forbidden` | Missing permission, including salary filters or sorts without `SALARY_READ` |
| 404 | `not-found` | Unknown resource, or an import job the caller may not see |
| 409 | `version-conflict` | Optimistic lock failure (body has `current_version`) |
| 409 | `duplicate` | Unique `employee_code` / `email`, including duplicates found at import commit |
| 409 | `invalid-state` | Wrong state, e.g. terminating a terminated employee, committing an expired or non-`DRY_RUN` import |
| 413 | `payload-too-large` | Upload over 4 MB |
| 415 | `unsupported-media-type` | Upload that isn't CSV or XLSX |
| 422 | `validation` | Field-level errors in a JSON body or query (`errors[]`) |
| 429 | `rate-limited` | Login failure limit, Ask per-user limit, or LLM provider 429 after one retry. Always sends `Retry-After` |
| 500 | `import-failed` | Import commit transaction failed; job marked `FAILED`, nothing written |
| 502 | `upstream-unavailable` | LLM provider 5xx, timeout, 4xx (e.g. malformed tool call) or invalid output after one repair retry |
| 503 | `feature-disabled` | Ask called with no `LLM_API_KEY` |

A dry-run with row errors is **not** an error response: `POST /imports` returns `201` with `errors[]` in the body.

## 6. API names

| Topic | Canonical |
|---|---|
| Base path | `/api/v1` |
| Money | `{ "amount_minor": int, "currency": "EUR" }` |
| USD figures | returned next to local ones, with `fx_as_of` (the oldest `as_of` among the rates used) |
| Pagination | `page`, `page_size` → `{ items, page, page_size, total }` |
| Sort | `sort=-current_base,last_name`; salary sort fields `current_base`, `current_total` |
| Filters | `q`, `country`, `department_id`, `job_role_id`, `level`, `employment_type`, `status`, `currency` (multi-value by repeating the key) |
| Salary range | `salary_min`, `salary_max` (minor units), `salary_basis=local\|usd`, `comp=base\|total` |
| Insight stats object | `{ count, min, p25, median, mean, p75, max, currency, suppressed }`, ints in minor units ([07](07-api-spec.md) §8.2) |
| Insight response extras | `population` (filters applied), `fx_as_of` when USD appears |
| Job-title split | `split_by_level=true` |
| Pay-equity views | `view=cohorts\|departments` |
| Import job | `id` (int), `status`, `format`, `filename`, `row_count`, `valid_count`, `error_count`, `errors[]`, `preview[]`, `expires_at` |
| Import row error | `{ row, column, code, message, value }`; codes include `duplicate_in_file`, `duplicate_in_db`, `unknown_value`, `too_many_decimals`, `required`, `invalid_format` |
| Import commit response | `{ id, status: "COMMITTED", inserted }` |
| Import commit allowed for | the job's creator or an `ADMIN` |
| Import headers | case-insensitive, trimmed, any order; unknown columns are an error |
| Formula escaping (export) | prefix `'` when a text cell starts with `=`, `+`, `-`, `@`, tab or CR |
| Feature flags | `GET /auth/me` → `features: { ask: bool }` (no separate status endpoint) |
| Server-side auth | Server Components and Server Actions send `Authorization: Bearer <JWT>` to `API_ORIGIN` |
| Login | client `fetch('/api/v1/auth/login')` through the rewrite, never a Server Action |
| Uploads | client `fetch` through the rewrite, never a Server Action (1 MB body limit) |

## 7. Environment variables

| Variable | Project | Values |
|---|---|---|
| `APP_ENV` | api | `development`, `test`, `production` (production enables the strict checks) |
| `DATABASE_URL` | api | `sqlite:///./dev.db` · `sqlite://` (tests) · Turso URL (no token in the URL) |
| `DATABASE_AUTH_TOKEN` | api | Turso token, passed through `connect_args`, never logged |
| `JWT_SECRET`, `JWT_TTL_MINUTES` | api | ≥ 32 random bytes in production · `480` |
| `COOKIE_SECURE` | api | `false` locally, forced `true` in production |
| `CORS_ORIGINS` | api | `http://localhost:3000` in development; empty in production (same origin) |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | api | Ask is disabled when `LLM_API_KEY` is empty |
| `ASK_RATE_LIMIT_PER_HOUR`, `ASK_MAX_STEPS` | api | `20` · `4` |
| `SEED_ADMIN_PASSWORD`, `SEED_HR_PASSWORD`, `SEED_VIEWER_PASSWORD` | seed | Production refuses defaults |
| `API_ORIGIN` | web | API base URL for the rewrite and server-side fetches; never exposed to the browser |
| `NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS` | web | `true` on the demo deployment only: `/login` lists the three demo accounts (names, emails, roles, never passwords). Inlined at build time |

## 8. Commands, files and resources

| Thing | Canonical |
|---|---|
| Local seed | `make seed` |
| Turso seed file | `make seed-turso` → `build/seed.db` → `turso db create salary-prod --from-file build/seed.db` |
| Turso database | `salary-prod` (production only; no preview DB) |
| Vercel projects | `salary-web` (root `frontend/`), `salary-api` (root `backend/`) |
| Seeded `changed_by` / audit `actor_id` | `null` (seed and system actions have no user) |
| `search_text` | `fold(first last code email)`: NFKD, strip accents, casefold. `muller` finds `Müller` |
| Eval results | `docs/ai/evals/results/<date>-<provider>-<model>.md` |
