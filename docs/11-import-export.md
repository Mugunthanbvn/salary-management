# 11 — Bulk Import & Export (CSV + XLSX)

> **Purpose:** Specify how HR moves employee and salary data in and out of the system with CSV and Excel files: the import template, validation pipeline, dry-run and all-or-nothing commit, safety rules, and role-aware export.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [06-data-model.md](06-data-model.md) · [07-api-spec.md](07-api-spec.md) · [08-security-rbac.md](08-security-rbac.md) · [13-frontend-ux.md](13-frontend-ux.md) · [14-testing-strategy.md](14-testing-strategy.md) · [17-deployment.md](17-deployment.md) · [19-performance.md](19-performance.md) · [adr/0012-bulk-import-dry-run.md](adr/0012-bulk-import-dry-run.md) · [adr/0011-audit-events.md](adr/0011-audit-events.md)

---

## 1. Why this exists

ACME's HR team **manages salaries in Excel today** (problem statement). Two consequences:

1. **Getting data in** must be painless and safe. A bad file must never half-load and corrupt records. Users must see *exactly* what is wrong, row by row, before anything is written.
2. **Getting data out** is still needed. HR will keep sharing spreadsheets with finance and leadership, so exports must respect permissions (no individual salaries for Viewers) and must not become an attack vector (CSV/Excel formula injection).

## 2. Scope

| In scope (v1) | Out of scope (v1) — reason |
|---|---|
| Import **new employees** with their current salary and components from **CSV or XLSX** | **Updating existing employees via file (upsert)**: more complex conflict semantics (which fields win, optimistic locking per row). Future work |
| Downloadable template (CSV and XLSX) | Importing salary *history* (multiple records per employee): the import creates the starting record only |
| Dry-run preview with per-row errors and duplicate detection | Partial commits ("import the valid rows only"): all-or-nothing is safer and simpler to reason about |
| All-or-nothing commit in one transaction | Background or async jobs: not needed at this size; serverless-friendly synchronous flow |
| Export of the filtered employee list as CSV or XLSX, role-aware | Scheduled or emailed exports |

> **Decided:** v1 import is **create-only**. A row whose `employee_code` or `email` already exists in the DB is reported as a duplicate error. Flagged in [03-clarifications.md](03-clarifications.md).

## 3. Permissions

| Action | Permission | Roles |
|---|---|---|
| Download template | `IMPORT` | HR_MANAGER, ADMIN |
| Upload → dry-run | `IMPORT` | HR_MANAGER, ADMIN |
| Commit a dry-run | `IMPORT` (and must be the job's creator or an `ADMIN`) | HR_MANAGER, ADMIN |
| Export employees **with** salary columns | `EXPORT` + `SALARY_READ` | HR_MANAGER, ADMIN |
| Export employees **without** salary columns | `EXPORT` | VIEWER (salary columns stripped) |

See [08-security-rbac.md](08-security-rbac.md) for the full matrix.

---

## 4. Import template

One row per employee. Header names are **case-insensitive and trimmed**. Column order does not matter. Unknown columns produce an error, so typos like `emial` are caught.

| Column | Type / format | Required | Rules | Example |
|---|---|---|---|---|
| `employee_code` | string | ✅ | Pattern `ACME-\d{6}` **(proposed)**; unique in file and DB | `ACME-010001` |
| `first_name` | string 1–100 | ✅ | Trimmed; Unicode allowed | `Jürgen` |
| `last_name` | string 1–100 | ✅ | Trimmed; Unicode allowed | `Müller` |
| `email` | email ≤ 254 | ✅ | Valid syntax; lowercased; unique in file and DB | `jurgen.muller@acme.example` |
| `job_role` | string | ✅ | Must match a title in the **controlled `job_roles` list** (case-insensitive exact match) | `Customer Success Manager` |
| `level` | enum | ✅ | `L1`–`L6` | `L2` |
| `employment_type` | enum | ✅ | `FULL_TIME`, `PART_TIME`, `CONTRACTOR` | `FULL_TIME` |
| `country` | ISO 3166-1 alpha-2 | ✅ | Must exist in `countries` | `DE` |
| `hire_date` | date `YYYY-MM-DD` (or an Excel date cell) | ✅ | Not in the future; not before 1970-01-01 | `2022-04-01` |
| `currency` | ISO 4217 | ⬜ | Defaults to the country's `default_currency`; if given, must equal it | `EUR` |
| `base_salary` | decimal, **major units**, annual | ✅ | > 0; at most as many decimals as the currency allows (JPY: 0, EUR: 2); no thousands separators | `52000.00` |
| `bonus_target` | decimal, major units, annual | ⬜ | ≥ 0; same precision rule | `4160.00` |
| `allowance_1_name` … `allowance_3_name` | string 1–50 | ⬜ | Required if the matching amount is present | `Transport` |
| `allowance_1_amount` … `allowance_3_amount` | decimal, major units, annual | ⬜ | > 0; precision rule | `1200.00` |
| `salary_effective_date` | date | ⬜ | Defaults to `hire_date`; not in the future; ≥ `hire_date` | `2022-04-01` |

Notes:
- **Up to 3 allowances per row (proposed).** That covers the seeded patterns (e.g. India: HRA + special allowance) without a nested format.
- Amounts are entered in **major units** because HR thinks in "52,000.00 EUR", not "5,200,000 cents". The parser converts to integer **minor units** using the currency exponent ([adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md)). An amount with more decimals than allowed (e.g. `1000.5` JPY) is an **error, never silently rounded**. Trailing zeros are fine (`1000.0` JPY is ¥1,000): only a non-zero digit past the currency's exponent is rejected.
- The imported salary record gets `reason = HIRE`, a `job_role_id` + `level` snapshot, and `changed_by` = the importing user ([06-data-model.md](06-data-model.md)).
- **Template download:** `GET /api/v1/imports/template?format=csv|xlsx`. The XLSX template has a header row, one example row, and **(proposed)** dropdown data validation for `job_role`, `level`, `employment_type`, `country`, and `currency`, plus a second read-only sheet "Reference" listing valid values.

---

## 5. Pipeline

```mermaid
flowchart LR
    A[Upload file<br/>POST /imports] --> B{Size ≤ 4 MB?<br/>type allowed?}
    B -- no --> X1[413 / 415 problem+json]
    B -- yes --> C[Parse<br/>CSV or XLSX → raw rows]
    C -- parse error --> X2[400 bad-request file-level error]
    C --> D[Normalize<br/>trim, case, dates, money → minor units]
    D --> E[Validate each row<br/>types, enums, reference data, rules]
    E --> F[Duplicate check<br/>in-file + against DB]
    F --> G[(import_jobs<br/>status=DRY_RUN<br/>rows + errors stored)]
    G --> H[Dry-run report to UI]
    H -- errors > 0 --> I[User fixes file,<br/>re-uploads]
    H -- errors = 0 --> J[POST /imports/:id/commit]
    J --> K{Re-validate duplicates<br/>job fresh? creator or ADMIN?}
    K -- conflict --> X3[409 problem+json]
    K -- ok --> L[Single transaction:<br/>employees + salary_records<br/>+ components + audit]
    L --> M[(import_jobs<br/>status=COMMITTED)]
    L -- any failure --> N[Rollback → status=FAILED]
```

### 5.1 Parsing (format-specific, thin)

Parsing is the **only** format-specific step. Both parsers produce the same `RawRow = dict[str, str | None]` plus a row number. Everything after that is shared, so validation is written and tested once ([adr/0012-bulk-import-dry-run.md](adr/0012-bulk-import-dry-run.md)).

**CSV**
- Encoding: **UTF-8, with or without BOM**. Excel's "CSV UTF-8" export adds a BOM, and it is stripped. If decoding fails (e.g. Excel's legacy "CSV (Comma delimited)", which is Windows-1252), the upload is rejected with: *"File is not UTF-8. In Excel choose File → Save As → 'CSV UTF-8 (Comma delimited)'."*
- Delimiter: comma. Quoting: RFC 4180. Header row required. Blank lines are ignored.
- Parsed with Python's `csv` module (streamed, no pandas).

**XLSX**
- Accepted extension `.xlsx` and MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`. **`.xlsm`, `.xls` and `.xlsb` are rejected** (macros or legacy formats).
- `openpyxl.load_workbook(file, read_only=True, data_only=True)`:
  - `data_only=True` reads **cached cell values, never formulas**. A formula cell with no cached value becomes an error: "Cell contains a formula without a value; paste values instead."
  - Macros are never executed (openpyxl doesn't execute anything; macro-enabled formats are rejected anyway).
- **`defusedxml`** is installed so openpyxl parses XML safely (protects against XML entity expansion attacks).
- **Zip-bomb guard:** reject if the total uncompressed size of the archive exceeds 50 MB.
- Reads the **first sheet**, or the sheet named `Employees` if present. A header row is required.
- Cell types: date cells → `date`; numeric cells → converted via `Decimal(repr(value))` to avoid float artefacts; everything else → string.

### 5.2 Normalization

- Trim whitespace. Lowercase `email`. Uppercase `country`, `currency`, `level`, `employment_type`.
- Dates accept ISO `YYYY-MM-DD` or a native Excel date. Ambiguous formats (`03/04/2022`) are rejected with a hint.
- Money: strip a leading currency symbol? **No.** Symbols and thousands separators are rejected with a clear message, to avoid locale ambiguity (`1.234,56` vs `1,234.56`). After trimming, an amount must be a plain ASCII decimal (`52000.00`, `-12.5`, `+7`): `Money.from_major` rejects `_` grouping, inner spaces, exponents (`1e3`), `12.` / `.5` and non-ASCII digits. XLSX numeric cells are turned into a `Decimal` by the parser (above) before this check.

### 5.3 Row validation

Pydantic models validate each row against the **same domain rules** the create-employee API uses (one source of truth). Reference data (job roles, countries, currencies with FX rates) is loaded **once** per import, not per row.

### 5.4 Duplicate detection

| Check | Key | Error code |
|---|---|---|
| Within the file | `employee_code` | `duplicate_in_file` (reported on the 2nd and later occurrences, pointing to the first row) |
| Within the file | `email` | `duplicate_in_file` |
| Against the DB | `employee_code` exists | `duplicate_in_db` |
| Against the DB | `email` exists | `duplicate_in_db` |

DB checks run as **one batched query per key** (`WHERE employee_code IN (...)`), not one per row.

### 5.5 Dry-run report

Stored in `import_jobs` and returned to the UI:

```json
{
  "id": 31,
  "status": "DRY_RUN",
  "filename": "q4-new-hires.xlsx",
  "format": "XLSX",
  "row_count": 248,
  "valid_count": 241,
  "error_count": 7,
  "expires_at": "2026-10-25T10:45:00Z",
  "summary": {
    "by_country": { "IN": 120, "US": 80, "DE": 41 },
    "total_base_by_currency": [ { "currency": "INR", "amount_minor": 1834500000 } ]
  },
  "errors": [
    { "row": 12, "column": "email",    "code": "duplicate_in_file", "message": "Same email as row 4", "value": "a.rao@acme.example" },
    { "row": 31, "column": "job_role", "code": "unknown_value",     "message": "‘Sr Engineer’ is not a known job role. Did you mean ‘Software Engineer’ (level L3)?", "value": "Sr Engineer" },
    { "row": 77, "column": "base_salary", "code": "too_many_decimals", "message": "JPY amounts can't have decimals", "value": "450000.5" }
  ],
  "preview": [ { "row": 2, "employee_code": "ACME-010001", "name": "Ananya Rao", "country": "IN", "job_role": "Software Engineer", "level": "L2", "base_salary": { "amount_minor": 1500000000, "currency": "INR" } } ]
}
```

- `row` numbers are **spreadsheet row numbers** (header = row 1), so the user can find the row in Excel.
- Messages are written for HR users, with a "did you mean" suggestion for near-miss job roles **(proposed: simple case-insensitive and edit-distance match)**.
- `preview` holds the first 50 valid rows **(proposed)**, for a sanity check in the UI.
- Department isn't an import column. It is **derived from `job_role`** ([06-data-model.md](06-data-model.md)).
- An **error report download** (CSV of `row, column, code, message, value`) is offered in the UI and generated client-side from the JSON.
- A dry-run with errors stays inspectable, but **cannot be committed**. The user fixes the file and re-uploads, which creates a new job.

### 5.6 Commit (all or nothing)

`POST /api/v1/imports/{id}/commit`

Preconditions (otherwise `409 Conflict` problem+json):
- `status == DRY_RUN` and `error_count == 0`.
- `expires_at` not passed: **24 hours** after the dry-run. This bounds the gap between validation and commit. The DB duplicate re-check below covers changes made in the meantime.
- Requested by the job's creator or an `ADMIN`.
- **DB duplicates re-checked**, because someone else may have created one of these employees since the dry-run.

Execution:
- **One DB transaction**: insert employees → salary records → salary components → audit event → mark the job `COMMITTED`.
- Bulk inserts (SQLAlchemy Core `insert()` with executemany, in chunks of 1,000), the same approach as the seed ([12-seed-data.md](12-seed-data.md)).
- A duplicate found at commit returns `409` problem+json `duplicate` with the conflicting rows. Any other exception rolls back, marks the job `FAILED` with `failure_reason`, and returns `500` problem+json `import-failed`. **No partial data is ever written.**
- Response: `{ id, status: "COMMITTED", inserted }`.

### 5.7 `import_jobs` lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRY_RUN: upload validated (errors may be > 0)
    DRY_RUN --> COMMITTED: commit (0 errors, fresh, same user, no new dupes)
    DRY_RUN --> FAILED: commit transaction error
    DRY_RUN --> EXPIRED: commit attempted after expires_at (refused with 409; job kept for audit)
    EXPIRED --> [*]
    COMMITTED --> [*]
    FAILED --> [*]
```

Stored fields (see [06-data-model.md](06-data-model.md)): `id`, `filename`, `format`, `status`, `row_count`, `error_count`, `errors` (JSON), **`payload` (JSON of normalized valid rows)**, `created_by`, `created_at`, `expires_at`, `committed_at`, `failure_reason`.

Why the payload is stored in the DB: **Vercel functions are stateless**. The commit request may hit a different instance, so the validated payload must be persisted between the two requests ([17-deployment.md](17-deployment.md)).

Retention **(proposed)**: the `payload` is cleared 7 days after the job ends (it contains salary data). Job metadata and errors are kept for audit.

### 5.8 Limits

| Limit | Value | Reason |
|---|---|---|
| Max upload size | **4 MB** | Vercel's 4.5 MB request body cap; a 10k-row CSV is ~1.5 MB |
| Max rows per file | **10,000** | Matches org size; keeps validation and commit within function time limits |
| XLSX uncompressed size | **50 MB** | Zip-bomb guard |
| Dry-run validity | **24 hours** | Bounds stale validation; duplicates are re-checked at commit anyway |
| Concurrent active dry-runs per user | **3 (proposed)** | Stops abuse and bloat |

Performance targets for a 10k-row import (parse + validate + dry-run < 5 s; commit < 30 s against Turso, checked against the spike's bulk-insert timing) are tracked in [19-performance.md](19-performance.md). Insert with IDs pre-allocated in Python, so no `RETURNING` is needed and `current_salary_record_id` is set on insert.

---

## 6. Export

`GET /api/v1/employees/export?format=csv|xlsx&<same filters as the list endpoint>`

### 6.1 Behaviour

- Applies **exactly the same filters** as `GET /api/v1/employees` (search, country, department, job role, level, status, employment type, currency, salary range). "What you see is what you export."
- As on the list endpoint, **salary-range filters and sorting by salary need `SALARY_READ`**. A Viewer export that includes them is rejected with `403` (filtering by salary could reveal individual pay).
- Sort order matches the list's current sort.
- Max rows: the whole filtered set (≤ 10k). A 10k-row CSV is ~1 MB and XLSX ~600 KB, both within Vercel's 4.5 MB response cap.
- Filename: `acme-employees-YYYY-MM-DD.csv|xlsx`, via `Content-Disposition`.
- CSV is written as **UTF-8 with BOM**, so Excel shows `Müller` and `José` correctly when the file is double-clicked.

### 6.2 Columns by role

| Column | HR_MANAGER / ADMIN | VIEWER |
|---|---|---|
| employee_code, first_name, last_name, email | ✅ | ✅ |
| department, job_role, level, employment_type | ✅ | ✅ |
| country, status, hire_date | ✅ | ✅ |
| currency | ✅ | ❌ |
| base_salary (major units) | ✅ | ❌ |
| bonus_target, allowances_total | ✅ | ❌ |
| total_comp (major units) | ✅ | ❌ |
| base_salary_usd, total_comp_usd + `fx_as_of` | ✅ **(proposed)** | ❌ |

- For Viewers, salary columns are **removed server-side**, not just hidden in the UI.
- Money is exported as major-unit decimal strings with the currency in its own column, e.g. `52000.00` + `EUR` (JPY: `4500000`).
- The export column order mirrors the import template where the two overlap **(proposed)**, so an export can be edited and become a future upsert file.

### 6.3 Formula-injection neutralisation (CSV and XLSX)

Spreadsheet apps execute cells that start with formula characters. A malicious name like `=HYPERLINK("http://evil","click")` could run when finance opens the export.

Rule (follows OWASP CSV Injection guidance): any **string** cell whose first character is `=`, `+`, `-`, `@`, tab (`\t`) or carriage return (`\r`) is prefixed with a single quote `'`.

- Applied to **all user-controlled text fields** (names, email, job role, allowance names) in both CSV and XLSX.
- Numeric columns are written as numbers (XLSX) or plain numeric strings (CSV), so negative numbers aren't affected. Salaries are positive anyway.
- XLSX: cells are written with an explicit string type, so openpyxl never interprets a leading `=` as a formula.
- Tested with a fixture employee named `=1+1` and `@SUM(A1)` in both formats ([14-testing-strategy.md](14-testing-strategy.md)).

### 6.4 Audit

Each export writes `export.download` to `audit_events` with: format, filters, row count, and `salary_included: true|false` ([adr/0011-audit-events.md](adr/0011-audit-events.md)).

---

## 7. Audit events (import and export)

| Action | When | `diff` payload |
|---|---|---|
| `import.dry_run` | Upload validated | `{ job_id, filename, format, row_count, error_count }` |
| `import.commit` | Commit succeeded | `{ job_id, inserted, employee_code_range }` |
| `import.fail` | Commit rolled back | `{ job_id, failure_reason }` |
| `export.download` | Export downloaded | `{ format, filters, row_count, salary_included }` |

**(Proposed)** A committed import writes **one summary event** rather than 10k per-employee events. The job ID links the summary to the stored rows.

---

## 8. Test plan (summary)

Detailed in [14-testing-strategy.md](14-testing-strategy.md):

- **Parsers:** CSV with and without BOM, Windows-1252 rejected, quoted commas, blank lines; XLSX date cells, numeric float artefacts, formula without cached value, `.xlsm` rejected, oversized archive rejected.
- **Parity:** the same dataset as CSV and as XLSX gives **identical** normalized rows and identical error lists.
- **Validation:** each rule with a failing row (unknown job role, bad level, too many decimals for JPY, future hire date, missing allowance name).
- **Duplicates:** in-file (code, email), against the DB, and a new duplicate created between dry-run and commit → 409.
- **Commit:** all rows created with salary records and components; an injected failure mid-transaction → nothing written, job `FAILED`.
- **Permissions:** VIEWER → 403 on import; another HR user can't commit someone else's job.
- **Export:** filters respected, Viewer columns stripped, formula-injection fixtures neutralised, BOM present, audit event written.

## 9. Open questions

- Create-only vs upsert in v1 → **create-only (decided)**. Upsert is future work: it needs per-field merge rules and per-row optimistic locking.
- 3 allowance column pairs per row → **(proposed)**. (Caps are settled: 4 MB, 10,000 rows, 50 MB uncompressed XLSX, 24 h dry-run expiry.)
- Include USD columns in the HR export → **(proposed: yes)**.
