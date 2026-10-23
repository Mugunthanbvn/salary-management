# ADR-0001: Single monorepo for backend, frontend, docs and AI tooling

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The assessment is reviewed as **one Git repository**. Reviewers want to see how the solution evolved through incremental commits, and want the code to sit next to the artifacts (requirements, ADRs, prompts, trade-offs). The system has two deployables: a FastAPI backend and a Next.js frontend. It also has shared contracts (OpenAPI → generated TypeScript client), shared docs, and shared AI tooling (`CLAUDE.md`, `.claude/`).

## Decision drivers

- Reviewers read one repo and one commit history.
- The API contract must stay in sync between backend and frontend (see [ADR-0014](0014-contract-first-openapi-client.md)).
- One CI pipeline, one `Makefile`, and one set of AI instructions.
- Small team (one developer + AI). Coordinating several repos costs more than it gives back.

## Considered options

1. **Monorepo**: `backend/`, `frontend/`, `docs/`, `.claude/` in one repo, with simple folder separation (no Nx/Turborepo).
2. **Polyrepo**: separate repos for API and UI.
3. **Monorepo with a JS build orchestrator** (Turborepo/Nx).

## Decision

**Option 1.** Plain folders in one repository:

```
/
├─ backend/        FastAPI app (uv)
├─ frontend/       Next.js app (pnpm)
├─ docs/           PRD, ADRs, design, AI artifacts
├─ .claude/        Claude Code settings, rules, skills, agents
├─ .github/        CI workflows, templates
├─ CLAUDE.md, AGENTS.md, Makefile, lefthook.yml, compose.yaml
```

The root `Makefile` is the single entry point and calls `uv` and `pnpm` underneath (see [15-tooling-devex.md](../15-tooling-devex.md)).

## Consequences

### Positive
- One story in the commit history. Each milestone PR can touch backend, frontend and docs together.
- A contract change and its generated client land in the same commit, and CI's `contract` job checks they stay in sync.
- Each AI rule file sits next to the code it governs.

### Negative / risks
- Two toolchains (Python + Node) in one repo, so the hooks and CI have to know about folders. Mitigation: lefthook's per-folder `root` option and path-filtered CI jobs.
- Two Vercel projects deploy from the same repo, each with its own root directory (see [17-deployment.md](../17-deployment.md)).
- No build orchestrator, so task caching is per-tool (uv and pnpm caches) rather than graph-aware. That's acceptable at this size.

## Links

- [05-architecture.md](../05-architecture.md), [15-tooling-devex.md](../15-tooling-devex.md), [17-deployment.md](../17-deployment.md)
