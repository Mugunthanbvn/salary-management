---
paths:
  - "backend/src/**/modules/*/router.py"
  - "backend/src/**/modules/*/schemas.py"
  - "frontend/src/lib/api/**"
---

# API contract rules

Source: [docs/07-api-spec.md](../../docs/07-api-spec.md) §1, [glossary](../../docs/glossary.md) §5–§6,
[ADR 0014](../../docs/adr/0014-contract-first-openapi-client.md).

- **Base path `/api/v1`.** Additive changes stay in v1; breaking changes would need `/api/v2`. Call them out.
- **Errors are RFC 9457 problem+json**: `type = https://acme.example/problems/<slug>`, slugs and statuses
  from glossary §5 only. Validation errors add `errors[]`. Every error body carries `request_id`.
- **Pagination:** `page` (≥ 1), `page_size` (default 25, max 100) → `{ items, page, page_size, total }`.
- **Sort:** `sort=-current_base,last_name`; fields from an allow-list; unknown field → 422.
  Default sort `last_name,first_name,id`.
- **Filters:** query params with glossary §6 names; multi-value by repeating the key.
- **Money:** `{ "amount_minor": int, "currency": "EUR" }`; USD figures next to local ones with `fx_as_of`.
- **Every request model** uses `extra="forbid"`. **Every route declares `response_model`** and its permission.
- `snake_case` fields, integer IDs in paths, dates `YYYY-MM-DD`, timestamps ISO-8601 UTC with `Z`.
- **After any router or schema change run `make api-sync`** and commit the regenerated
  `frontend/openapi.json` and `frontend/src/lib/api/schema.d.ts`. The CI contract job fails on drift.
- Never hand-edit `schema.d.ts` or `openapi.json` (a hook blocks it).
