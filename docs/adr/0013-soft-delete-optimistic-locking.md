# ADR-0013: Soft delete (terminate/reactivate) and optimistic locking

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The brief asks for create, view, update and **deactivate** employee records. Hard-deleting an employee would destroy salary history and audit context that HR and finance rely on. Several HR users may edit the same employee at the same time, and a silent "last write wins" can lose updates, for example two people correcting the same record.

## Decision drivers

- Keep history (pay and audit) intact.
- Prevent lost updates without heavyweight locking.
- A simple REST contract.

## Considered options

1. **Soft delete via `status` + optimistic locking via a `version` column.**
2. Hard delete + pessimistic row locks.
3. Soft delete, no concurrency control.

## Decision

**Option 1.**
- `employees.status ∈ {ACTIVE, TERMINATED}` plus `termination_date`. Endpoints: `POST /employees/{id}/terminate` and `/reactivate` (audited). Terminated employees are excluded from insights by default and filterable in lists.
- `employees.version INTEGER` is incremented on every update. `PATCH /employees/{id}` must include the `version` the client read. On a mismatch the API returns **409 Conflict** (problem+json), and the UI shows "This record was changed by someone else. Reload to see the latest."
- No hard-delete endpoint exists.

## Consequences

### Positive
- History is never lost, and concurrent edits are detected.
- Easy to test (a stale version gives 409).

### Negative / risks
- Personal data is retained indefinitely. A retention or erasure policy (e.g. GDPR right to erasure) is out of scope and documented as future work.
- Clients must carry the `version` through edit forms.

## Links

- [06-data-model.md](../06-data-model.md), [07-api-spec.md](../07-api-spec.md), [13-frontend-ux.md](../13-frontend-ux.md)
