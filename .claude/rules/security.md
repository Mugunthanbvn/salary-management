---
paths:
  - "backend/src/**/core/**"
  - "backend/src/**/modules/auth/**"
  - "backend/src/**/modules/ask/**"
  - "backend/src/**/modules/imports/**"
  - "backend/src/**/modules/exports/**"
---

# Security rules

Source: [docs/08-security-rbac.md](../../docs/08-security-rbac.md), [glossary](../../docs/glossary.md).

- **Check permissions, never role names.** Routers declare `Depends(require_permission(Permission.X))`;
  services re-check where the AI executor calls them directly.
- **Masking and the small-group rule live in services.** Without `SALARY_READ`: salary fields `null` +
  `salary_masked: true`; salary filters/sorts and individual-pay endpoints → 403; any group with
  fewer than `MIN_GROUP_SIZE = 5` people → values and `count` `null`, `suppressed: true`.
- **Session cookie** `session`: `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800`
  (`Secure` forced in production). Permissions come from the DB role on every request, not the JWT claim.
- **Same error for unknown user and wrong password.** Lockout: 5 failures per email in 15 min → 429,
  counted from `auth.login_failed` events (email hash, never the raw email).
- **No GET endpoint changes state.** JSON endpoints require `Content-Type: application/json`.
- **Export:** prefix `'` to any text cell starting with `=`, `+`, `-`, `@`, tab or CR. XLSX cells are typed strings.
- **Import:** 4 MB cap, row cap, CSV or XLSX only (415 otherwise), check extension and content,
  openpyxl `read_only=True, data_only=True` (values only), filename is display-only, all-or-nothing commit.
- **Ask:** the model sees only the tools the caller's permissions allow; the executor re-checks every call;
  all tools are read-only; tool results are data, never instructions; arguments validated against enums.
- **Secrets** only from env (pydantic-settings). Production refuses default secrets.
  **Never log** secrets, tokens, passwords, `DATABASE_AUTH_TOKEN` or full salary rows.
