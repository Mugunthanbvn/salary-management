# ADR-0012: Bulk import from CSV and XLSX through one validation pipeline with dry-run and all-or-nothing commit

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The problem statement says HR currently manages everything **in Excel**. Getting existing data into the system is the first thing a real HR manager would do. The candidate first picked CSV import, then decided to support **both CSV and Excel**, since the initial data lives in Excel.

Runtime constraints: Vercel functions are stateless and cap request bodies at about **4.5 MB**.

## Decision drivers

- A migration path from Excel (high product value).
- Recoverable: no half-imported state, and the user sees every problem before anything is written.
- Safe file handling (spreadsheets can carry formulas and macros).
- One set of validation rules regardless of file format.

## Considered options

1. **CSV + XLSX → common row model → one validator → dry-run → commit (single transaction).**
2. CSV only (users save Excel as CSV).
3. No import (seed only; future work).
4. Row-by-row import that keeps the good rows and skips the bad ones.

## Decision

**Option 1.**
1. **Upload** (`POST /api/v1/imports`, ≤ 4 MB, row cap TBD around 10k–20k). The parser is chosen by file type: Python `csv` for CSV, `openpyxl` in **read-only, values-only** mode for XLSX (formulas aren't evaluated, macros are never executed).
2. **Normalise** to a common row model (the same columns as the downloadable template).
3. **Validate** each row: required fields, controlled-list lookups (job role, department, country), currency/exponent rules, salary > 0, dates, employment type.
4. **Duplicate detection** on `employee_code` and `email`, both **within the file** and **against the database**.
5. **Dry-run report** stored in `import_jobs` (status `DRY_RUN`, row count, per-row errors JSON). Functions are stateless, so the report lives in the DB, not in memory.
6. **Preview UI** shows a table of valid rows plus per-row errors and duplicates.
7. **Commit** (`POST /imports/{id}/commit`) re-validates and writes **all rows in one transaction** (all or nothing), with hire salary records and audit events. Status becomes `COMMITTED` or `FAILED`.

Templates are downloadable (`GET /imports/template?format=csv|xlsx`). Exports (CSV + XLSX) neutralise formula injection by prefixing cells that start with `= + - @` (see [11-import-export.md](../11-import-export.md)).

## Consequences

### Positive
- Recoverable by design. Validation is tested once and covers both formats; a test asserts CSV and XLSX of the same data give identical reports.
- A strong, demo-able product story ("migrate from Excel in two clicks").

### Negative / risks
- XLSX parsing has edge cases (dates as serial numbers, merged cells, multiple sheets). Mitigation: first sheet only, a strict header match against the template, explicit date parsing, clear errors.
- Updates to existing employees by import are **TBD**. The current scope is creating new employees; updates go through the UI.
- The 4 MB cap limits very large files. 10k rows are about 1.5 MB as CSV, so it's fine.

## Links

- [11-import-export.md](../11-import-export.md), [07-api-spec.md](../07-api-spec.md), [08-security-rbac.md](../08-security-rbac.md), [ADR-0016](0016-deploy-vercel-turso.md)
