# ADR-0009: Permission-based RBAC with three roles, salary masking and a small-group rule

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

Salary data is among the most confidential data a company holds. Competitor submissions mostly had a **single shared login**. The candidate chose three roles (Admin / HR Manager / Viewer) and asked what a good setup looks like in real HR systems. Real systems also have line managers (own team only) and employee self-service, but both need a reporting hierarchy and employee logins, which is big scope.

A subtle privacy problem: an **aggregate over a very small group reveals individual pay**. If "Principal Engineer, Japan" has one person, its average *is* that person's salary.

## Decision drivers

- Least privilege for confidential pay.
- Easy to extend (new roles shouldn't need code changes everywhere).
- Enforcement on the server, never only in the UI.
- Demonstrable privacy thinking.

## Considered options

1. **Three roles mapped to permissions; Viewer sees aggregates only; small-group suppression.**
2. Three roles; Viewer sees everything read-only.
3. A fourth role, HR Staff (edit profiles but not salaries: separation of duties).
4. A single role.

## Decision

**Option 1.**

Code checks **permissions, never role names** (`require_permission(Permission.SALARY_READ)`). Roles are a mapping in `core/permissions.py`, so adding a role is one entry.

| Permission | ADMIN | HR_MANAGER | VIEWER |
|---|---|---|---|
| `EMPLOYEE_READ` (name, dept, title, country, status) | ✅ | ✅ | ✅ |
| `SALARY_READ` (individual salary + history) | ✅ | ✅ | ❌ (masked) |
| `EMPLOYEE_WRITE` (create/edit/terminate/reactivate) | ✅ | ✅ | ❌ |
| `SALARY_WRITE` (record salary change) | ✅ | ✅ | ❌ |
| `IMPORT` | ✅ | ✅ | ❌ |
| `EXPORT` | ✅ (with salary) | ✅ (with salary) | ✅ (**without** the salary columns) |
| `INSIGHTS_READ` (aggregates, pay-equity cohorts) | ✅ | ✅ | ✅ (small groups suppressed) |
| `ASK` | ✅ | ✅ | ✅ (aggregate tools only) |
| `USER_ADMIN`, `FX_ADMIN`, `REFERENCE_ADMIN` | ✅ | ❌ | ❌ |
| `AUDIT_READ` | ✅ | ❌ | ❌ |

**Small-group rule:** for users without `SALARY_READ`, any aggregate computed over **fewer than 5 employees** returns `null` with a `suppressed: true` flag, and the UI shows "—" with a tooltip. The threshold `MIN_GROUP_SIZE = 5` is a named constant. It's applied **in the service layer**, so the dashboard, exports and the AI Ask tools all inherit it.

Exact permission names may be refined during implementation; the matrix semantics are fixed.

## Consequences

### Positive
- Real least privilege, plus a privacy safeguard that's rare in competitor submissions.
- One enforcement point shared by REST endpoints and AI tools ([ADR-0015](0015-ai-ask-tool-calling.md)).
- The authz matrix becomes a table-driven pytest suite (role × endpoint → expected status).

### Negative / risks
- More tests and more UI states (masked cells, suppressed values).
- The small-group rule cuts detail for Viewers in sparse cohorts, which is intended.
- Line-manager and self-service roles are out of scope (documented).

## Links

- [08-security-rbac.md](../08-security-rbac.md), [09-insights-pay-equity.md](../09-insights-pay-equity.md), [07-api-spec.md](../07-api-spec.md), [14-testing-strategy.md](../14-testing-strategy.md)
