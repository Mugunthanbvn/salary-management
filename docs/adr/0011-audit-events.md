# ADR-0011: Append-only `audit_events` written in the same transaction as the change

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

For confidential HR data, the organisation must be able to answer: *who changed this salary? who exported the payroll file? who changed this user's role or the FX rates?* Salary history already records `changed_by` for pay changes, but exports, imports, profile edits, admin actions, logins and AI questions weren't covered.

## Decision drivers

- Complete accountability for sensitive actions.
- An audit entry must never be lost when the change succeeds, and must never exist when the change fails.
- Low implementation cost.

## Considered options

1. **An `audit_events` table written by the service layer inside the same DB transaction.**
2. Application logs only (structlog).
3. Database triggers.
4. An external audit or log service.

## Decision

**Option 1.**
- `audit_events(id, actor_id, action, entity, entity_id, diff JSON, at)`. Append-only: no update or delete endpoints exist.
- Actions include (final list in [08-security-rbac.md](../08-security-rbac.md)): `employee.created/updated/terminated/reactivated`, `salary.changed`, `import.dry_run/committed`, `export.generated` (with filters and format), `user.created/role_changed/deactivated`, `fx.updated`, `auth.login_succeeded/failed`, `ask.question` (question + tools used).
- `diff` stores before/after for changed fields. **Salary values in diffs are only visible to users with `AUDIT_READ` (Admin).**
- Written by services in the same transaction as the domain write, so they're atomic.
- Admin UI: `/admin/audit` with filters (actor, action, entity, date).
- The per-user rate limit on AI Ask counts `ask.question` events, which works across stateless serverless instances ([ADR-0015](0015-ai-ask-tool-calling.md)).

## Consequences

### Positive
- Atomic, queryable, testable: each mutating endpoint test asserts its audit event.
- It also serves as the rate-limit store in a stateless environment.

### Negative / risks
- Every mutating service must remember to write the event. Mitigation: a shared helper, tests per action, and a reviewer-agent checklist item.
- The table grows without bound. A retention policy is out of scope (documented).

## Links

- [08-security-rbac.md](../08-security-rbac.md), [06-data-model.md](../06-data-model.md), [14-testing-strategy.md](../14-testing-strategy.md)
