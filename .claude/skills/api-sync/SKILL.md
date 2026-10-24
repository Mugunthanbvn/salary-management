---
name: api-sync
description: Use after any change to a FastAPI router or Pydantic schema. Regenerates the OpenAPI spec and the frontend TypeScript types, then fixes the frontend call sites the contract change broke.
---

# /api-sync

1. Run `make api-sync`. It exports `frontend/openapi.json` from the FastAPI app (no server needed),
   regenerates `frontend/src/lib/api/schema.d.ts` with openapi-typescript, then runs `tsc --noEmit`.
2. If `tsc` fails, list the frontend call sites affected by the contract change and fix them,
   or reconsider the API change if it breaks the contract without a good reason.
3. Make sure the MSW handlers still typecheck and the frontend tests pass (`cd frontend && pnpm vitest run`).
4. Call out any breaking change (removed or renamed field, changed type or status) in the commit body.
5. Commit the regenerated files with the feature commit, or alone as `build(api): regenerate client`.
   Never hand-edit `openapi.json` or `schema.d.ts`.
