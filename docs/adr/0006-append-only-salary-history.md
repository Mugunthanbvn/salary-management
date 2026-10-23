# ADR-0006: Append-only salary history with a denormalized current salary

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

HR needs to know not only what someone earns now but how they got there: hire salary, merit raises, promotions, market adjustments, corrections. That enables insights such as "average raise last year by department". At the same time, list and insight queries over 10k employees must stay fast and simple.

## Decision drivers

- Full, tamper-evident history (who changed what, when, why).
- Fast reads of the current salary for lists, filters and aggregates.
- Keep scope tight. No scheduling or approval workflows.

## Considered options

1. **Append-only `salary_records` + a denormalized current salary on `employees`**, updated in the same transaction.
2. **Only `salary_records`**; derive the current salary with a window query ("latest effective_date ≤ today") on every read.
3. **Only a current salary column** (no history).
4. **Bi-temporal / future-dated records** (scheduled raises).

## Decision

**Option 1.**
- `salary_records(employee_id, base_minor, currency, job_role_id, level, effective_date, reason, changed_by, created_at)`. Rows are **never updated or deleted**. A mistake is fixed by appending a `CORRECTION` record.
- **Snapshot of `job_role_id` + `level`** on each record, so the history can show "L2 → L3, Promotion, +12%" even after the employee's current role changes.
- Reasons: `HIRE`, `PROMOTION`, `MERIT`, `MARKET_ADJUSTMENT`, `CORRECTION`.
- Components (allowances, bonus target) hang off each record (see [ADR-0010](0010-compensation-components.md)).
- `employees.current_base_minor`, `current_total_minor` and `currency` are updated **only by the salary service**, in the same transaction as the new record and its audit event.
- **No future-dated changes**: `effective_date ≤ today` is validated. Scheduled raises are out of scope.

## Consequences

### Positive
- A complete audit trail of pay. Raise analytics come for free.
- Current-salary reads are a simple indexed column, with no window functions on hot paths.

### Negative / risks
- Denormalization can drift if anything else writes the columns. Mitigation: a single write path (the service), a test asserting that the current salary always equals the latest record, and a CLAUDE.md rule.
- Corrections add rows rather than editing them, so the UI must explain the "correction" entries.

## Links

- [06-data-model.md](../06-data-model.md), [07-api-spec.md](../07-api-spec.md), [ADR-0011](0011-audit-events.md)
