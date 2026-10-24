# ADR-0019: One Vercel project with services instead of two projects

- **Status:** Accepted (refines [ADR-0016](0016-deploy-vercel-turso.md))
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

ADR 0016 planned two Vercel projects (`salary-web`, `salary-api`) joined by a Next.js rewrite, so the session cookie stays first-party. Vercel now offers **services**: several frameworks in one project, routed by top-level rewrites on one domain, with private service-to-service **bindings**.

## Decision drivers

- One domain, so the cookie is first-party without a proxy hop.
- One set of environment variables and one deploy instead of two.
- No change to application behaviour or to the local `make dev` workflow.

## Considered options

1. **Two projects + Next.js rewrite** (ADR 0016): works, but two deploys, two env sets, and an extra hop for every `/api` call.
2. **One project with services**: `backend` (FastAPI) and `frontend` (Next.js) in the root `vercel.json`; `/api/*` → `backend`, `/*` → `frontend`; the frontend calls the backend server-side through a `BACKEND_URL` binding.

## Decision

We choose **option 2**. Vercel passes the original path to the service, so FastAPI keeps its `/api/v1` routes. `lib/api/origin.ts` reads `BACKEND_URL` at call time (bindings resolve at runtime, not at build time) and falls back to `API_ORIGIN` for local development; `next.config.ts` adds its `/api` proxy only when `API_ORIGIN` is set. The region (`bom1`) moves to the root `vercel.json`.

## Consequences

### Positive
- One URL for reviewers, one deploy, one set of env vars; no extra hop for browser `/api` calls.

### Negative / risks
- Services are a Beta feature. If they misbehave, the two-project setup of ADR 0016 still works: delete the root `vercel.json`, create two projects and set `API_ORIGIN` on the web project before its build.

## Links

- [17-deployment.md](../17-deployment.md) §2, [glossary](../glossary.md) §7–§8
- https://vercel.com/docs/services, https://vercel.com/docs/services/routing
