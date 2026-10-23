# ADR-0014: Contract-first frontend types generated from FastAPI's OpenAPI schema

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

FastAPI generates an OpenAPI document from the Pydantic schemas automatically. The frontend needs exact request and response types. Hand-written TS types drift silently, and drift between API and UI is a common bug source, especially when AI generates code on both sides.

## Decision drivers

- End-to-end type safety.
- Drift caught in CI, not in production.
- A minimal runtime footprint and full control over fetching (Server Components + Server Actions).

## Considered options

1. **openapi-typescript** (types only) + **openapi-fetch** (tiny typed fetch client).
2. **Hey API `@hey-api/openapi-ts`** (full SDK, Zod schemas, TanStack Query plugins).
3. **Orval** (React Query/SWR hooks, mocks, Zod).
4. Hand-written types.

## Decision

**Option 1.**
- `make api-sync`: export `openapi.json` from the FastAPI app (no running server needed), then `openapi-typescript` generates `frontend/src/lib/api/schema.d.ts`, then `tsc`.
- `openapi-fetch` is wrapped in one server-side helper that forwards the auth cookie ([ADR-0008](0008-fastapi-auth-same-origin-rewrite.md)).
- The generated files are **committed** and **must not be hand-edited**: a Claude Code PreToolUse hook blocks edits, and a lefthook/CI check enforces it.
- The CI `contract` job regenerates the client and runs `git diff --exit-code`, so it fails if the backend changed without a regenerated client.

## Consequences

### Positive
- A typo in an API field becomes a compile error. Very small runtime cost.
- Contract changes are visible in PR diffs.

### Negative / risks
- No generated hooks or Zod schemas: form validation schemas (zod) are hand-written and kept consistent by tests.
- The OpenAPI output quality depends on precise Pydantic models (explicit response models on every route), which is good discipline anyway.

## Links

- [07-api-spec.md](../07-api-spec.md), [15-tooling-devex.md](../15-tooling-devex.md), [ADR-0017](0017-toolchain.md)
