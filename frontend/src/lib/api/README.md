# API client

This folder holds the API helpers and `schema.d.ts`, the TypeScript types generated from the FastAPI OpenAPI spec by `make api-sync` (it writes `frontend/openapi.json`, then runs `pnpm api:types`).
Both generated files are never edited by hand. API types come only from `schema.d.ts`; the typed openapi-fetch client will live next to it.
