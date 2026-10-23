# 07 — API Specification

> The HTTP contract between the Next.js frontend and the FastAPI backend: every endpoint, its permission, inputs, outputs and errors.

**Status:** Draft for review · **Last updated:** 2026-10-24
**Related:** [05-architecture.md](05-architecture.md) · [06-data-model.md](06-data-model.md) · [08-security-rbac.md](08-security-rbac.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [11-import-export.md](11-import-export.md) · ADRs [0008](adr/0008-fastapi-auth-same-origin-rewrite.md), [0009](adr/0009-permission-rbac-small-group-rule.md), [0013](adr/0013-soft-delete-optimistic-locking.md), [0014](adr/0014-contract-first-openapi-client.md)

The **source of truth** at build time is FastAPI's generated OpenAPI document (`/api/v1/openapi.json`). The TypeScript client is generated from it, and CI fails if the committed client drifts ([ADR 0014](adr/0014-contract-first-openapi-client.md)). This document describes intent. Field names and shapes below are **(proposed)** until each milestone's tests pin them.

---

## 1. Conventions

### 1.1 Basics

| Topic | Convention |
|---|---|
| Base path | `/api/v1` (served under the web origin through the Next.js rewrite, see [05-architecture.md](05-architecture.md) §4.3) |
| Versioning | URL prefix. Breaking changes would go to `/api/v2`; additive changes stay in v1 |
| Format | JSON (`application/json`), UTF-8. File endpoints use `multipart/form-data` (upload) or a file response (download) |
| Field casing | `snake_case`, matching Pydantic models and the generated TS types |
| IDs | Integers in paths (`/employees/42`); `employee_code` is a searchable field, not a path key |
| Dates | `YYYY-MM-DD`; timestamps ISO-8601 UTC with `Z` |
| Auth | Session JWT in the `session` httpOnly cookie (browser) or `Authorization: Bearer <JWT>` (server-side fetches). Both are accepted |
| Request ID | Optional `X-Request-ID` in; always echoed in the response header and in error bodies |
| Unknown fields | Rejected (`extra="forbid"`) with 422, so typos are not silently ignored |

### 1.2 Money object

Every monetary value uses one shape. Amounts are integers in **minor units** of the given currency ([06-data-model.md](06-data-model.md) §5).

```json
{ "amount_minor": 1200000, "currency": "EUR" }
```

When a USD equivalent is relevant, it is returned next to the local value, together with the FX date:

```json
{
  "local": { "amount_minor": 1200000, "currency": "EUR" },
  "usd":   { "amount_minor": 1296000, "currency": "USD" },
  "fx_as_of": "2026-10-01"
}
```

The frontend formats with `Intl.NumberFormat` using the currency exponent and never does arithmetic on money ([13-frontend-ux.md](13-frontend-ux.md)).

### 1.3 Pagination

Offset pagination (10k rows; deep-page cost is negligible, see [19-performance.md](19-performance.md)).

| Param | Default | Limits |
|---|---|---|
| `page` | `1` | ≥ 1 |
| `page_size` | `25` | 1–100 |

```json
{ "items": [ ... ], "page": 2, "page_size": 25, "total": 812 }
```

### 1.4 Filtering and sorting

- Filters are query parameters. Multi-value filters repeat the key: `?country=DE&country=FR`.
- `sort` takes a comma-separated whitelist of fields; a `-` prefix means descending: `sort=-current_base,last_name`. Unknown sort fields → 422. There is never raw column interpolation.
- Default sort: `last_name,first_name,id` (stable).

### 1.5 Errors: RFC 9457 `application/problem+json`

```json
{
  "type": "https://acme.example/problems/version-conflict",
  "title": "Version conflict",
  "status": 409,
  "detail": "Employee 42 was modified by someone else. Reload and try again.",
  "instance": "/api/v1/employees/42",
  "request_id": "6f1c2b9e-...",
  "current_version": 8
}
```

Validation errors add an `errors` array:

```json
{
  "type": "https://acme.example/problems/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "2 fields are invalid.",
  "errors": [
    { "loc": ["body", "base", "amount_minor"], "code": "too_many_decimals", "message": "JPY has no minor unit; send a whole number of yen." },
    { "loc": ["body", "job_role_id"], "code": "not_found", "message": "Unknown job role 999." }
  ]
}
```

| Status | `type` slug | When |
|---|---|---|
| 400 | `bad-request` | Malformed request that is not a field validation (e.g. unreadable file) |
| 401 | `unauthenticated` | Missing/invalid/expired token, or the user is inactive |
| 403 | `forbidden` | Authenticated but missing the required permission |
| 404 | `not-found` | Unknown resource |
| 409 | `version-conflict` | Optimistic lock failure ([ADR 0013](adr/0013-soft-delete-optimistic-locking.md)) |
| 409 | `duplicate` | Unique constraint (employee_code, email) |
| 409 | `invalid-state` | e.g. terminating an already terminated employee, committing a non-DRY_RUN import |
| 413 | `payload-too-large` | Upload > 4 MB |
| 415 | `unsupported-media-type` | Upload that is not CSV/XLSX |
| 422 | `validation` | Field-level validation errors |
| 429 | `rate-limited` | Ask rate limit or provider rate limit; includes `Retry-After` |
| 503 | `feature-disabled` / `upstream-unavailable` | Ask disabled (no key) or LLM provider down |

### 1.6 Permission notation

Each endpoint lists the permission it requires (see [08-security-rbac.md](08-security-rbac.md) for the role → permission matrix). **Public** means no authentication. Field-level masking for users without `SALARY_READ` is described per endpoint.

### 1.7 Masking for users without `SALARY_READ` (VIEWER)

- Individual salary fields (`current_base`, `current_total`, `components`) are returned as `null`, and the item carries `"salary_masked": true`.
- Endpoints that exist only to reveal individual pay (salary history, top earners, cohort member lists) return **403**.
- Filtering or sorting by individual salary returns **403**. Otherwise repeated range queries could reveal one person's pay.
- Aggregates are allowed, but any group with fewer than **3** people is suppressed: values `null`, `"suppressed": true` (the small-group rule, [ADR 0009](adr/0009-permission-rbac-small-group-rule.md)).

---

## 2. Endpoint index

| Method | Path | Permission |
|---|---|---|
| GET | `/health` | Public |
| POST | `/auth/login` | Public |
| POST | `/auth/logout` | Authenticated |
| GET | `/auth/me` | Authenticated |
| GET | `/reference` | `EMPLOYEE_READ` |
| GET | `/countries` | `EMPLOYEE_READ` |
| PATCH | `/countries/{code}` | `REFERENCE_ADMIN` |
| GET | `/employees` | `EMPLOYEE_READ` (salary filters/sorts need `SALARY_READ`) |
| POST | `/employees` | `EMPLOYEE_WRITE` + `SALARY_WRITE` |
| GET | `/employees/{id}` | `EMPLOYEE_READ` (masked without `SALARY_READ`) |
| PATCH | `/employees/{id}` | `EMPLOYEE_WRITE` |
| POST | `/employees/{id}/terminate` | `EMPLOYEE_WRITE` |
| POST | `/employees/{id}/reactivate` | `EMPLOYEE_WRITE` |
| GET | `/employees/{id}/salary-history` | `SALARY_READ` |
| POST | `/employees/{id}/salary-changes` | `SALARY_WRITE` |
| GET | `/employees/export` | `EXPORT` (salary columns only with `SALARY_READ`) |
| GET | `/imports/template` | `IMPORT` |
| POST | `/imports` | `IMPORT` |
| GET | `/imports/{id}` | `IMPORT` |
| POST | `/imports/{id}/commit` | `IMPORT` |
| GET | `/insights/overview` | `INSIGHTS_READ` |
| GET | `/insights/by-department` | `INSIGHTS_READ` |
| GET | `/insights/by-job-title` | `INSIGHTS_READ` |
| GET | `/insights/distribution` | `INSIGHTS_READ` |
| GET | `/insights/department-cost` | `INSIGHTS_READ` |
| GET | `/insights/top-earners` | `INSIGHTS_READ` + `SALARY_READ` |
| GET | `/insights/raises` | `INSIGHTS_READ` |
| GET | `/insights/pay-equity` | `INSIGHTS_READ` |
| GET | `/insights/pay-equity/cohort` | `INSIGHTS_READ` + `SALARY_READ` |
| GET | `/pay-bands` | `INSIGHTS_READ` |
| GET | `/fx-rates` | `INSIGHTS_READ` |
| PUT | `/fx-rates/{currency}` | `FX_ADMIN` |
| GET | `/users` | `USER_ADMIN` |
| POST | `/users` | `USER_ADMIN` |
| PATCH | `/users/{id}` | `USER_ADMIN` |
| GET | `/audit-events` | `AUDIT_READ` |
| GET | `/ask/status` | `ASK` |
| POST | `/ask` | `ASK` |

---

## 3. Health

### `GET /health`: Public

Performs a trivial DB read **and** write (an upsert into a heartbeat row **(proposed)**) so the deploy spike proves the database is writable ([17-deployment.md](17-deployment.md)).

```json
200 { "status": "ok", "db": "ok", "version": "1.0.0" }
503 { "status": "degraded", "db": "error" }   // problem+json body in practice
```

---

## 4. Auth

### `POST /auth/login`: Public

```json
// request
{ "email": "hr@acme.example", "password": "••••••••" }

// 200 response (+ Set-Cookie: session=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800)
{
  "user": { "id": 2, "email": "hr@acme.example", "full_name": "Harriet Rao", "role": "HR_MANAGER" },
  "permissions": ["EMPLOYEE_READ", "EMPLOYEE_WRITE", "SALARY_READ", "SALARY_WRITE", "INSIGHTS_READ", "EXPORT", "IMPORT", "ASK"]
}
```

Errors: 401 `unauthenticated` with the **same message** for unknown email and wrong password ("Invalid email or password"), so the endpoint doesn't reveal which emails exist. 429 after repeated failures **(proposed)**, see [08-security-rbac.md](08-security-rbac.md) §9.

### `POST /auth/logout`: Authenticated

Clears the cookie (`Max-Age=0`). 204. Writes `auth.logout`.

### `GET /auth/me`: Authenticated

Same body as the login response. Used by the frontend to render role-aware navigation.

---

## 5. Reference data

### `GET /reference`: `EMPLOYEE_READ`

One call for every dropdown and for validating filters. Small and cacheable per session.

```json
{
  "countries": [ { "code": "DE", "name": "Germany", "default_currency": "EUR", "is_active": true } ],
  "departments": [ { "id": 4, "name": "Customer Success" } ],
  "job_roles": [ { "id": 17, "title": "Customer Success Manager", "department_id": 4, "family": "G_AND_A" } ],
  "levels": [ { "code": "L1", "label": "Associate" }, { "code": "L3", "label": "Senior" } ],
  "employment_types": ["FULL_TIME", "PART_TIME", "CONTRACTOR"],
  "currencies": [ { "code": "JPY", "exponent": 0 }, { "code": "EUR", "exponent": 2 } ],
  "salary_change_reasons": ["HIRE", "PROMOTION", "MERIT", "MARKET_ADJUSTMENT", "CORRECTION"]
}
```

### `GET /countries`: `EMPLOYEE_READ` · `PATCH /countries/{code}`: `REFERENCE_ADMIN`

```json
// PATCH request (all optional)
{ "name": "Germany", "default_currency": "EUR", "is_active": true }
```

Writes `reference.country.update` with the diff. `default_currency` must be a supported currency (422 otherwise).

---

## 6. Employees

### 6.1 `GET /employees`: `EMPLOYEE_READ`

| Query param | Type | Notes |
|---|---|---|
| `q` | string | Search name / employee code / email (folded, see [06-data-model.md](06-data-model.md) §6.4). Min 2 chars |
| `country` | string[] | ISO alpha-2 |
| `department_id` | int[] | |
| `job_role_id` | int[] | "Designation" |
| `level` | string[] | `L1`..`L6` |
| `employment_type` | string[] | |
| `status` | string[] | Default `ACTIVE` |
| `currency` | string[] | |
| `salary_min`, `salary_max` | int (minor units) | **Requires `SALARY_READ`.** Requires exactly one `currency`, or `salary_basis=usd` for USD-normalized comparison |
| `salary_basis` | `local` \| `usd` | Default `local` |
| `comp` | `base` \| `total` | Which amount the salary filter/sort uses. Default `base` |
| `sort` | string | Whitelist: `last_name`, `first_name`, `employee_code`, `hire_date`, `country`, `level`, `current_base`*, `current_total`* (*needs `SALARY_READ`) |
| `page`, `page_size` | int | See §1.3 |

```json
// 200
{
  "items": [
    {
      "id": 4217,
      "employee_code": "ACME-004217",
      "first_name": "Priya",
      "last_name": "Sharma",
      "email": "priya.sharma.4217@acme.example",
      "job_role": { "id": 3, "title": "Software Engineer" },
      "department": { "id": 1, "name": "Engineering" },
      "level": "L3",
      "employment_type": "FULL_TIME",
      "country_code": "IN",
      "status": "ACTIVE",
      "hire_date": "2021-03-15",
      "current_base":  { "amount_minor": 240000000, "currency": "INR" },
      "current_total": { "amount_minor": 362400000, "currency": "INR" },
      "salary_masked": false,
      "version": 7
    }
  ],
  "page": 1, "page_size": 25, "total": 812
}
```

For a VIEWER: `current_base` and `current_total` are `null`, and `salary_masked` is `true`.

Errors: 403 if a salary filter/sort is used without `SALARY_READ`; 422 for a salary range without a single currency (and no `salary_basis=usd`).

### 6.2 `POST /employees`: `EMPLOYEE_WRITE` + `SALARY_WRITE`

Creates the employee **and** its `HIRE` salary record in one transaction.

```json
// request
{
  "employee_code": "ACME-010001",            // optional; generated when omitted
  "first_name": "Lena",
  "last_name": "Müller",
  "email": "lena.mueller@acme.example",
  "job_role_id": 17,
  "level": "L2",
  "employment_type": "FULL_TIME",
  "country_code": "DE",
  "hire_date": "2026-10-01",
  "salary": {
    "currency": "EUR",                        // defaults to the country's default_currency
    "base_minor": 5400000,
    "components": [
      { "type": "ALLOWANCE", "name": "Transport", "amount_minor": 60000 },
      { "type": "BONUS_TARGET", "name": "Target bonus", "amount_minor": 432000 }
    ],
    "note": "Offer accepted 2026-09-12"
  }
}
```

`201` returns the employee detail (as §6.3) with a `Location` header. Errors: 409 `duplicate` (code/email), 422 (unknown role, inactive country, hire date in the future, too many decimals for the currency).

### 6.3 `GET /employees/{id}`: `EMPLOYEE_READ`

Returns the list item fields plus `current_salary` (record id, effective date, components) and `termination_date`. Masked as in §1.7 for users without `SALARY_READ`.

### 6.4 `PATCH /employees/{id}`: `EMPLOYEE_WRITE`

Profile fields only (names, email, employment type, country). **Salary, role and level change only through salary changes**, so history always explains them.

```json
// request
{ "version": 7, "email": "priya.s@acme.example", "employment_type": "PART_TIME" }
```

- `version` is **required**: the value the client last read.
- `200` returns the updated employee with `version: 8`.
- `409 version-conflict` if the stored version differs, with `current_version`. The UI shows "This record changed, reload" ([13-frontend-ux.md](13-frontend-ux.md)).
- Writes `employee.update` with `{field: [old, new]}`.

### 6.5 `POST /employees/{id}/terminate` · `POST /employees/{id}/reactivate`: `EMPLOYEE_WRITE`

```json
// terminate request
{ "version": 8, "termination_date": "2026-10-31", "note": "Resigned" }
// reactivate request
{ "version": 9 }
```

200 with the updated employee. 409 `invalid-state` if already in the target state; 409 `version-conflict`; 422 if `termination_date < hire_date`.

### 6.6 `GET /employees/{id}/salary-history`: `SALARY_READ`

```json
{
  "employee_id": 4217,
  "records": [
    {
      "id": 90211, "effective_date": "2021-03-15", "reason": "HIRE",
      "job_role": { "id": 3, "title": "Software Engineer" }, "level": "L2",
      "base":  { "amount_minor": 180000000, "currency": "INR" },
      "total": { "amount_minor": 270000000, "currency": "INR" },
      "components": [ { "type": "ALLOWANCE", "name": "HRA", "amount_minor": 72000000 } ],
      "base_change_pct": null,
      "changed_by": null, "note": null, "created_at": "2026-10-20T10:00:00Z"
    },
    {
      "id": 90212, "effective_date": "2023-04-01", "reason": "PROMOTION",
      "job_role": { "id": 3, "title": "Software Engineer" }, "level": "L3",
      "base":  { "amount_minor": 216000000, "currency": "INR" },
      "base_change_pct": "12.50",
      "changed_by": { "id": 2, "full_name": "Harriet Rao" }
    }
  ]
}
```

Records are ordered by `(effective_date, id)`. `base_change_pct` is a decimal string computed in `domain/` (and `null` when the currency changed).

### 6.7 `POST /employees/{id}/salary-changes`: `SALARY_WRITE`

```json
// request
{
  "version": 9,
  "effective_date": "2026-10-01",
  "reason": "PROMOTION",
  "job_role_id": 3,          // optional; defaults to current
  "level": "L4",             // optional; defaults to current
  "currency": "INR",         // optional; defaults to current
  "base_minor": 260000000,
  "components": [ { "type": "ALLOWANCE", "name": "HRA", "amount_minor": 104000000 } ],
  "note": "Annual cycle 2026"
}
```

Rules (from [06-data-model.md](06-data-model.md) §4.6):
- `effective_date` ≤ today, ≥ `hire_date`, ≥ the latest existing effective date.
- `PROMOTION` requires a higher `level` or a different `job_role_id` (422 otherwise).
- The employee must be `ACTIVE` (409 `invalid-state`).
- `components` replaces the component set for the new record. Components are **not** inherited implicitly; the UI pre-fills them from the current record.

201 returns the new record and the updated employee `version`. Writes `salary.change`.

### 6.8 `GET /employees/export`: `EXPORT`

Accepts **all filters of §6.1** plus `format=csv|xlsx`. Streams a file:

- `Content-Disposition: attachment; filename="employees-2026-10-24.csv"`.
- Columns depend on permission: without `SALARY_READ`, salary columns are omitted entirely (not blank).
- Every cell starting with `=`, `+`, `-`, `@`, tab or carriage return is prefixed with `'` (formula-injection protection, [08-security-rbac.md](08-security-rbac.md) §7).
- Writes `export.download` with the filters used and the row count.

Full column list and format details: [11-import-export.md](11-import-export.md).

---

## 7. Imports (dry-run, then commit)

### 7.1 `GET /imports/template?format=csv|xlsx`: `IMPORT`

Downloads an empty template with the header row (and, for XLSX, a second sheet listing valid job roles, countries, levels and currencies).

### 7.2 `POST /imports`: `IMPORT`

`multipart/form-data` with field `file`. Max 4 MB; max 10,000 data rows **(proposed)**. Accepts `.csv` (UTF-8, with or without BOM) and `.xlsx` (values only, see [11-import-export.md](11-import-export.md)).

Runs parse → validate → duplicate checks (within the file and against the DB). **Nothing is written to employee tables.**

```json
// 201
{
  "id": 31,
  "status": "DRY_RUN",
  "format": "XLSX",
  "filename": "acme-germany.xlsx",
  "row_count": 412,
  "valid_count": 409,
  "error_count": 3,
  "errors": [
    { "row": 18, "column": "email", "code": "duplicate_in_db", "message": "Email already used by ACME-002210." },
    { "row": 40, "column": "job_title", "code": "unknown_value", "message": "\"Sr Engineer\" is not a known job role. Did you mean \"Senior Software Engineer\"?" },
    { "row": 77, "column": "base_salary", "code": "too_many_decimals", "message": "JPY has no minor unit." }
  ],
  "preview": [ { "row": 2, "employee_code": "ACME-010002", "full_name": "Lena Müller", "country_code": "DE", "base": { "amount_minor": 5400000, "currency": "EUR" } } ],
  "expires_at": "2026-10-25T09:12:00Z"
}
```

Errors: 413, 415, 400 (unreadable file / header mismatch, reported with the expected headers).

### 7.3 `GET /imports/{id}`: `IMPORT`

Returns the stored job (same shape). Only the creator or an ADMIN can see it (404 otherwise).

### 7.4 `POST /imports/{id}/commit`: `IMPORT`

- Requires `status=DRY_RUN`, `error_count=0` and not expired; otherwise 409 `invalid-state`.
- Re-runs duplicate checks against the DB (data may have changed since the preview); new conflicts → 409 with the conflicting rows, nothing written.
- Inserts all employees + `HIRE` salary records in **one transaction**; any failure rolls back everything.
- 200 `{ "id": 31, "status": "COMMITTED", "inserted": 409 }`. Writes `import.commit` (plus `import.dry_run` at upload).

---

## 8. Insights

### 8.1 Common query parameters

| Param | Default | Notes |
|---|---|---|
| `country` | — | ISO alpha-2. When set, statistics are in that country's **local currency** |
| `department_id`, `job_role_id`, `level` | — | Narrow the population |
| `employment_type` | `FULL_TIME` | Part-timers would distort averages; the override is explicit ([09-insights-pay-equity.md](09-insights-pay-equity.md)) |
| `status` | `ACTIVE` | |
| `comp` | `base` | `base` or `total` (base + allowances + bonus target) |

There is **no** `period` parameter: annual is returned and the UI divides by 12 for the monthly toggle.

Every response includes a `population` echo (the filters actually applied) and `fx_as_of` whenever USD appears.

### 8.2 Stats object

```json
{
  "count": 412,
  "min": 3600000, "p25": 4800000, "median": 5400000, "mean": 5523000, "p75": 6300000, "max": 14500000,
  "currency": "EUR",
  "suppressed": false
}
```

All values are integers in minor units of `currency`. Percentiles use **linear interpolation** (the same result as SQL `PERCENTILE_CONT`); interpolated and mean values are rounded **half-even** to the minor unit. Full definitions are in [09-insights-pay-equity.md](09-insights-pay-equity.md). For callers without `SALARY_READ`, a group with `count < 5` returns `"suppressed": true` and nulls every value except `count` (the count is also nulled **(proposed)**, to avoid confirming that one person exists in a narrow slice).

### 8.3 `GET /insights/overview`

```json
{
  "population": { "employment_type": ["FULL_TIME"], "status": ["ACTIVE"], "comp": "base" },
  "headcount": 9012,
  "total_payroll_usd": { "amount_minor": 82345600000, "currency": "USD" },
  "fx_as_of": "2026-10-01",
  "by_country": [
    {
      "country_code": "DE",
      "local": { "count": 702, "min": 3600000, "p25": 4800000, "median": 5400000, "mean": 5523000, "p75": 6300000, "max": 14500000, "currency": "EUR", "suppressed": false },
      "usd":   { "median": 5832000, "mean": 5964840, "currency": "USD" }
    }
  ]
}
```

### 8.4 `GET /insights/by-department`

Optional `country`. With a country: stats in local currency per department. Without: stats in USD per department (each employee converted at read time) and `fx_as_of`.

```json
{ "currency": "EUR", "groups": [ { "department": { "id": 4, "name": "Customer Success" }, "stats": { "...": "Stats object" } } ] }
```

### 8.5 `GET /insights/by-job-title`

`country` **required** (titles are compared within one labour market). Returns `groups[]` keyed by `job_role` with stats, optionally split by `level` (`split_by_level=true`).

### 8.6 `GET /insights/distribution`

`country` required, or `basis=usd` for an org-wide histogram. `buckets` (default 20, 5–50).

```json
{ "currency": "EUR", "bucket_width": 500000, "buckets": [ { "from": 3500000, "to": 4000000, "count": 41 } ] }
```

For callers without `SALARY_READ`, buckets with `count < 5` are merged into neighbours or shown as `"<5"` **(proposed)**.

### 8.7 `GET /insights/department-cost`

Total compensation cost per department in **USD** (sum of converted amounts), with `fx_as_of`. Optional `country`.

### 8.8 `GET /insights/top-earners`: requires `SALARY_READ`

`country` required; `n` (default 10, max 50); `direction=top|bottom`. Returns employee summaries with local amounts. 403 for VIEWER.

### 8.9 `GET /insights/raises`

`from`, `to` (dates; default the last 12 months), `group_by=department|country|reason`. Uses `salary_records` (excluding `HIRE` and `CORRECTION` from raise percentages).

```json
{ "from": "2025-10-24", "to": "2026-10-24", "groups": [ { "key": "Engineering", "count": 2410, "avg_raise_pct": "4.10", "by_reason": { "MERIT": 2100, "PROMOTION": 290, "MARKET_ADJUSTMENT": 20 } } ] }
```

### 8.10 `GET /insights/pay-equity`

Compa-ratio = employee **base** ÷ **pay band midpoint** for their job role + level + country (local currency). See [09-insights-pay-equity.md](09-insights-pay-equity.md) §3.8 and `pay_bands` in [06-data-model.md](06-data-model.md). The `comp` parameter is not accepted here (bands are base-only). Params: `view=cohorts|departments` (default `cohorts`), `country`, `department_id`.

`view=cohorts`:

```json
{
  "view": "cohorts",
  "thresholds": { "low": "0.80", "high": "1.20" },
  "cohorts": [
    {
      "job_role": { "id": 17, "title": "Customer Success Manager" }, "level": "L2", "country_code": "DE",
      "stats": { "count": 41, "p25": 4300000, "median": 4800000, "p75": 5300000, "currency": "EUR", "suppressed": false },
      "band": { "min": 4176000, "mid": 5220000, "max": 6264000, "currency": "EUR" },
      "median_compa_ratio": "0.92",
      "underpaid_count": 14, "overpaid_count": 1
    }
  ],
  "summary": { "employees_evaluated": 9012, "employees_without_band": 0, "employees_flagged_underpaid": 168, "employees_flagged_overpaid": 61 }
}
```

`view=departments` (systemic-gap view; `country` required): `groups[]` keyed by department with `count`, `median_compa_ratio`, `mean_compa_ratio`, `pct_below_band`, `underpaid_count`, `overpaid_count`, `below_threshold` (median compa-ratio < 0.95, **proposed**), `suppressed`.

Flags: `underpaid` = compa-ratio < 0.80 (below band minimum); `overpaid` = compa-ratio > 1.20 (above band maximum). Values exactly 0.80 or 1.20 count as within band, and the comparison uses the unrounded ratio. Thresholds are server settings matching the band width (`min = 0.8 × mid`, `max = 1.2 × mid`), not request parameters. For a VIEWER, groups with `count < 5` return counts, ratios and stats as `null` with `suppressed: true`; band values stay visible.

### 8.11 `GET /insights/pay-equity/cohort`: requires `SALARY_READ`

`job_role_id`, `level`, `country` required. Returns the band and each cohort member with `employee_code`, name, base, `compa_ratio` (decimal string, 2 dp) and flag `UNDERPAID` (< 0.80) / `IN_BAND` (0.80–1.20 inclusive) / `OVERPAID` (> 1.20). 403 for VIEWER. Viewing it writes an `insights.pay_equity_drilldown` audit event **(proposed)**.

### 8.12 `GET /pay-bands`: `INSIGHTS_READ`

Read-only list of bands, filterable by `country`, `job_role_id`, `level`: `{ job_role_id, level, country_code, currency, min, mid, max, effective_from }`. Bands are seeded; editing them is out of scope for v1.

---

## 9. FX rates

### `GET /fx-rates`: `INSIGHTS_READ`

```json
{ "rates": [ { "currency": "INR", "rate_to_usd": "0.01198", "as_of": "2026-10-01", "source": "Static snapshot (illustrative)" } ] }
```

### `PUT /fx-rates/{currency}`: `FX_ADMIN`

```json
{ "rate_to_usd": "0.01201", "as_of": "2026-10-20", "source": "Manual update" }
```

`rate_to_usd` must be a positive decimal string with at most 10 decimal places **(proposed)**. The USD rate cannot be changed (422). Writes `fx.update` with old/new rate.

---

## 10. Users (admin)

| Endpoint | Body | Notes |
|---|---|---|
| `GET /users` | — | Paginated; never returns password hashes |
| `POST /users` | `{email, full_name, role, password}` | Password policy: ≥ 12 chars **(proposed)**. 409 on duplicate email |
| `PATCH /users/{id}` | `{full_name?, role?, is_active?, password?}` | An admin cannot demote or deactivate **themselves**, and the last active ADMIN cannot be removed (409 `invalid-state`) **(proposed)** |

All changes write `user.create` / `user.update` (role changes show `[old, new]`; password changes are logged as `"password": "changed"` without values).

---

## 11. Audit events

### `GET /audit-events`: `AUDIT_READ`

Filters: `actor_id`, `action` (prefix match, e.g. `salary.`), `entity`, `entity_id`, `from`, `to`; paginated; newest first.

```json
{
  "items": [
    { "id": 5512, "at": "2026-10-24T08:01:12Z", "actor": { "id": 2, "full_name": "Harriet Rao" },
      "action": "salary.change", "entity": "employee", "entity_id": "4217",
      "diff": { "level": ["L3", "L4"], "base_minor": [216000000, 260000000] }, "request_id": "6f1c..." }
  ],
  "page": 1, "page_size": 50, "total": 1302
}
```

---

## 12. Ask about pay

### `GET /ask/status`: `ASK`

```json
{ "enabled": true, "provider": "gemini", "rate_limit_per_hour": 20, "remaining": 17 }
```

`enabled: false` when no `LLM_API_KEY` is configured; the UI then hides the feature.

### `POST /ask`: `ASK`

```json
// request: the client keeps the conversation; only the last ~6 turns are sent
{
  "messages": [
    { "role": "user", "content": "Are we underpaying anyone in Germany?" },
    { "role": "assistant", "content": "Yes, one team stands out..." },
    { "role": "user", "content": "And in India?" }
  ]
}

// 200
{
  "answer": "No department in India is significantly below its band...",
  "figures": [ { "label": "Median, Customer Success, IN", "value": { "amount_minor": 180000000, "currency": "INR" } } ],
  "tool_calls": [ { "name": "get_pay_equity_outliers", "args": { "country": "IN" }, "summary": "9 cohorts, 0 flagged below 0.8" } ],
  "caveats": ["Amounts in INR. USD figures use FX rates as of 2026-10-01."],
  "dashboard_link": "/insights/pay-equity?country=IN"
}
```

Limits: message `content` ≤ 1,000 chars **(proposed)**, ≤ 6 turns, ≤ 4 tool steps. Errors: 429 `rate-limited` (per-user limit or provider 429, with `Retry-After`), 503 `feature-disabled`, 503 `upstream-unavailable`. Full design: [10-ai-ask-design.md](10-ai-ask-design.md).
