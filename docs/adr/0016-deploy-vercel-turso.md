# ADR-0016: Deploy on Vercel (web + API projects) with Turso, all on free tiers

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The brief requires "fully functional deployed software". The candidate set two constraints: **free**, and **popular free options for this stack, not our own instances**. Reviewers may open the link days or weeks after submission, so nothing may expire or sleep for long.

Research (Oct 2026):
- **Vercel** hosts Next.js natively and now runs **FastAPI with zero config** as Python functions (Fluid compute). Hobby limits: about 300 s max duration, a **4.5 MB request/response body** limit, and a read-only filesystem except `/tmp`.
- **Render free:** Docker web service, sleeps when idle (about 30–50 s cold start), **no persistent disk** on free.
- **Fly.io:** no free tier for new users (trial of 2 VM-hours or 7 days, card required).
- **Railway:** 30-day trial with $5 credit, then the $5/mo Hobby plan.
- **Turso:** hosted libSQL/SQLite, free tier with about 5 GB and 500M reads / 10M writes a month, **no sleeping**.
- **Neon:** free Postgres, 0.5 GB per project, suspends compute after inactivity.

## Decision drivers

- $0, with no trial expiry during review.
- Persistent data.
- Short cold starts.
- A popular, recognisable stack.
- Compatible with [ADR-0002](0002-sqlite-everywhere-turso.md) (SQLite) and [ADR-0008](0008-fastapi-auth-same-origin-rewrite.md) (same-origin rewrite).

## Considered options

1. **Vercel (Next.js) + Vercel (FastAPI functions) + Turso.**
2. Vercel + **Render** free (FastAPI Docker) + Neon Postgres.
3. Vercel + **Fly.io** (FastAPI + SQLite on a volume, about $2–5/mo).
4. Vercel + **Railway** (FastAPI + SQLite on a volume, $5/mo).
5. **Self-host** on the candidate's existing Oracle Cloud Always-Free VM via Coolify (SQLite on a block volume, path routing, Litestream backups).
6. Vercel + Vercel functions + **Neon** Postgres.

### Notes on the rejected options
- **Option 2:** about 50 s cold starts; prod DB on Postgres (dialect drift).
- **Options 3 and 4:** the simplest plain-SQLite setup and the most mature driver, but **not free**; trial expiry could take the demo down mid-review.
- **Option 5:** technically strong ($0, always on, real disk, same origin), but **rejected by the candidate**: "no Coolify, not our own instances; use popular free options". Ops burden and the risk of Oracle reclaiming idle free VMs also count against it.
- **Option 6:** viable, and kept as the **fallback** if the Turso Python driver proves unreliable (switch by changing `DATABASE_URL`).

## Decision

**Option 1.**
- **Web project:** root `frontend/`, Next.js. `next.config.ts` rewrites `/api/:path*` to the API project.
- **API project:** root `backend/`, FastAPI zero-config entrypoint (declared in `pyproject.toml` `[tool.vercel]`, exact form TBD at the spike). Function region pinned to match the Turso region.
- **Database:** Turso, same region. Migrations and seed run **from CI or locally**, never inside a function. The seed builds a local SQLite file and uploads it (`turso db create --from-file`).
- **Previews:** Vercel preview deployment per PR.
- **Day-1 deploy spike (milestone 1):** `/api/health` does a DB read and write via the Turso driver, behind the web rewrite, with a test cookie verified in Safari.

## Consequences

### Positive
- $0, nothing sleeps for long (about 1–2 s function cold start vs about 50 s on Render), preview URLs per PR, one platform for both apps.

### Negative / risks
- Serverless constraints:
  - The 4.5 MB body limit caps import files at 4 MB.
  - Import dry-run state lives in the DB (`import_jobs`).
  - `NullPool` connections ([ADR-0003](0003-sync-sqlalchemy-serverless.md)).
- Dependency on Turso's young Python driver. Mitigated by the spike and the Neon fallback.
- Free-tier terms can change. Mitigated by the documented fallback paths in [17-deployment.md](../17-deployment.md).

## Links

- [17-deployment.md](../17-deployment.md), [04-research.md](../04-research.md), [ADR-0002](0002-sqlite-everywhere-turso.md), [ADR-0008](0008-fastapi-auth-same-origin-rewrite.md)
