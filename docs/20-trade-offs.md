# Trade-offs

> Every major choice, the alternatives we considered, and why we chose what we did — prepared for the design-discussion interview.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [04-research.md](04-research.md) · [05-architecture.md](05-architecture.md) · [15-tooling-devex.md](15-tooling-devex.md) · ADRs in [adr/](adr/)

---

Each section follows: **Chosen → Alternatives → Why → What we give up → When we'd revisit.** ADRs hold the formal record.

## 1. Repository layout — monorepo
- **Chosen:** one repo with `backend/`, `frontend/`, `docs/`, `.claude/`.
- **Alternatives:** separate repos per app.
- **Why:** one commit history tells the whole story; contract changes (API + client) land atomically; one CI.
- **Give up:** independent release cadence (irrelevant here).
- **Revisit:** if teams/apps split ownership.
- ADR: [adr/0001-monorepo.md](adr/0001-monorepo.md)

## 2. Database — SQLite everywhere (Turso in production)
- **Chosen:** SQLite file locally, in-memory for tests, Turso (hosted libSQL) in production; SQLAlchemy ORM + Alembic; DB chosen by `DATABASE_URL`.
- **Alternatives:**
  - Postgres everywhere (Docker locally, Neon in prod) — more "enterprise", but heavier local setup and slower tests.
  - SQLite dev/test + Postgres prod — common, but dialect drift (e.g. percentile functions) is exactly the bug seen in a competitor repo.
  - SQLite on a VM/volume (Fly, Railway, own VM) — simplest SQLite story but not free (or rejected: no own instances).
- **Why:** fits the scale (~10 MB); brief suggests SQLite; one dialect means identical results everywhere; reviewer runs with zero setup; Turso is free and doesn't sleep.
- **Give up:** a young Python driver for Turso; single-writer concurrency; network round-trips to Turso from functions.
- **Mitigation:** day-1 deploy spike; Neon fallback via URL; Postgres CI job proves portability; same-region deploy.
- **Revisit:** many concurrent writers, > ~1M rows, or need for Postgres-only features.
- ADR: [adr/0002-sqlite-everywhere-turso.md](adr/0002-sqlite-everywhere-turso.md)

## 3. Sync vs async SQLAlchemy
- **Chosen:** sync SQLAlchemy; FastAPI runs sync endpoints in a threadpool; `NullPool` in serverless.
- **Alternatives:** async SQLAlchemy (aiosqlite/asyncpg).
- **Why:** light CRUD at 10k scale; simpler code and tests; avoids event-loop pitfalls; Turso async driver support is even less mature.
- **Give up:** maximum concurrency per instance (serverless scales out anyway).
- ADR: [adr/0003-sync-sqlalchemy-serverless.md](adr/0003-sync-sqlalchemy-serverless.md)

## 4. Money representation
- **Chosen:** integer minor units (BIGINT) + ISO 4217 code + per-currency exponent.
- **Alternatives:** DECIMAL/NUMERIC; floats; strings.
- **Why:** exact; portable (SQLite has no true DECIMAL); fast integer aggregation.
- **Give up:** must always apply the exponent when formatting/parsing (centralised in a `Money` value object).
- ADR: [adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md)

## 5. FX conversion at read time
- **Chosen:** admin-maintained FX table (rate to USD as a decimal string, as-of date, source); convert only when reading; never store converted values.
- **Alternatives:** store USD alongside local amounts; live FX API.
- **Why:** history never shifts when rates change; deterministic tests; transparent (rate date shown).
- **Give up:** no automatic rate updates; USD figures are "illustrative" not accounting-grade.
- ADR: [adr/0005-fx-read-time-conversion.md](adr/0005-fx-read-time-conversion.md)

## 6. Salary history model
- **Chosen:** append-only `salary_records` (with job role + level snapshot) + denormalised current salary on `employees`, updated in the same transaction; no future-dated changes.
- **Alternatives:** current salary only; event sourcing; bitemporal model with scheduled changes.
- **Why:** full history and audit with fast reads; simple invariants.
- **Give up:** scheduled raises; denormalisation must be maintained by a single service path (tested).
- ADR: [adr/0006-append-only-salary-history.md](adr/0006-append-only-salary-history.md)

## 7. Where statistics are computed
- **Chosen:** pure Python domain functions (median, percentiles, compa-ratio) fed by SQL that returns sorted amounts per group.
- **Alternatives:** SQL `percentile_cont` (Postgres only); window-function percentiles in SQL; pandas.
- **Why:** unit-testable without a DB; identical on SQLite and Postgres; milliseconds at 10k rows.
- **Give up:** doesn't scale to millions of rows without change.
- **Revisit:** at ~1M rows → `percentile_cont` or materialised views on Postgres (see [19-performance.md](19-performance.md)).
- ADR: [adr/0007-pure-python-stats.md](adr/0007-pure-python-stats.md)

## 8. Authentication and the browser ↔ API path
- **Chosen:** FastAPI owns auth (argon2 + JWT in an httpOnly cookie); Next.js `rewrites` makes `/api/*` same-origin; Server Components forward the cookie.
- **Alternatives considered:**

| Alternative | Why rejected |
|---|---|
| Auth.js v5 Credentials → FastAPI | Library in maintenance mode; roles would still need enforcing in FastAPI |
| Better Auth in Next.js + JWKS | Auth split across two services; more to explain and test |
| Bearer token in localStorage (classic SPA) | XSS can steal token; no SSR for logged-in data |
| Cross-site cookie (`SameSite=None`) | Safari/Firefox block third-party cookies — demo may fail for reviewers |
| Shared custom domain (`app.` / `api.`) | Clean, but costs money |
| FastAPI serves Next static export | Loses Next.js SSR/Server Actions |
| Hosted auth (Clerk/Auth0) | Hides the engineering; roles in a third party |
| Full BFF service | Unnecessary — a rewrite rule achieves same-origin |

- **Give up:** dependency on Vercel rewrites (portable to any reverse proxy).
- ADR: [adr/0008-fastapi-auth-same-origin-rewrite.md](adr/0008-fastapi-auth-same-origin-rewrite.md)

## 9. Authorisation model
- **Chosen:** three roles mapped to permissions; code checks permissions; Viewer salary masking; small-group rule (n < 5 hidden for Viewer).
- **Alternatives:** two roles; role-name checks; four roles with HR Staff (separation of duties); Viewer sees everything read-only.
- **Why:** least privilege for confidential data; extensible (new role = one mapping line); prevents re-identification through tiny aggregates.
- **Give up:** more test cases (authz matrix).
- ADR: [adr/0009-permission-rbac-small-group-rule.md](adr/0009-permission-rbac-small-group-rule.md)

## 10. Compensation scope
- **Chosen:** base + components table (`ALLOWANCE`, `BONUS_TARGET`); total comp toggle; annual stored, monthly displayed.
- **Alternatives:** base only; base + bonus % field; full components including equity/commission.
- **Why:** base-only comparisons mislead across countries (e.g. India's HRA); components stay simple.
- **Give up:** equity, commission, benefits.
- ADR: [adr/0010-compensation-components.md](adr/0010-compensation-components.md)

## 11. Audit
- **Chosen:** append-only `audit_events` written by the service layer in the same transaction.
- **Alternatives:** DB triggers; external log service; salary history only.
- **Why:** portable across SQLite/Postgres; testable; covers exports, imports, admin actions — not just salary changes.
- ADR: [adr/0011-audit-events.md](adr/0011-audit-events.md)

## 12. Bulk import
- **Chosen:** CSV + XLSX through one pipeline: parse → validate → duplicate check → dry-run stored in `import_jobs` → all-or-nothing commit.
- **Alternatives:** CSV only; row-by-row partial import; background job queue.
- **Why:** HR lives in Excel; dry-run + single transaction is recoverable; serverless-friendly (state in DB).
- **Give up:** files > 4 MB (Vercel body limit); no async processing.
- ADR: [adr/0012-bulk-import-dry-run.md](adr/0012-bulk-import-dry-run.md)

## 13. Deletion and concurrency
- **Chosen:** soft delete (terminate/reactivate) + optimistic locking (`version` → 409).
- **Alternatives:** hard delete; pessimistic locks; last-write-wins.
- **Why:** HR records must be retained and reversible; prevents silent lost updates.
- **Give up:** no data-erasure workflow (**TBD** for real-world GDPR needs).
- ADR: [adr/0013-soft-delete-optimistic-locking.md](adr/0013-soft-delete-optimistic-locking.md)

## 14. API contract
- **Chosen:** FastAPI OpenAPI → openapi-typescript + openapi-fetch; CI fails on drift.
- **Alternatives:** hand-written types; Hey API / Orval full SDK generation; tRPC (not applicable across Python/TS).
- **Why:** end-to-end type safety with minimal generated code.
- ADR: [adr/0014-contract-first-openapi-client.md](adr/0014-contract-first-openapi-client.md)

## 15. AI "Ask about pay"
- **Chosen:** read-only tool calling over the existing insight services; one OpenAI-compatible adapter; Gemini free default, Groq alternative; FakeLLM for tests; eval set.
- **Alternatives:** text-to-SQL; Claude (paid); no AI feature; streaming answers.
- **Why:** answers always match the dashboard; no SQL injection surface; role-safe; $0; deterministic tests.
- **Give up:** free-tier rate limits; Gemini free tier may train on prompts (acceptable only for synthetic data); no streaming in v1.
- ADR: [adr/0015-ai-ask-tool-calling.md](adr/0015-ai-ask-tool-calling.md)

## 16. Hosting
- **Chosen:** Vercel (web) + Vercel (FastAPI functions) + Turso — all free.
- **Alternatives:** Render free (no disk, ~50 s cold start); Fly.io/Railway (trial expiry, ~$5/month); own VM with Coolify (rejected by user).
- **Why:** $0, always on, nothing expires during review, preview deploys per PR.
- **Give up:** serverless constraints (body size, stateless, no background jobs).
- ADR: [adr/0016-deploy-vercel-turso.md](adr/0016-deploy-vercel-turso.md)

## 17. Toolchain highlights
| Choice | Over | Reason |
|---|---|---|
| Pyright strict | mypy, Pyrefly, ty | Highest conformance; same engine as editor |
| ESLint + Prettier | Biome | Next.js + react-hooks rule parity |
| lefthook | pre-commit, husky | Monorepo-aware, no runtime dependency |
| Dependabot | Renovate | Built in, less setup |
| Makefile | just, npm scripts | Universal single entry point |
| PR per milestone, merge commits | Squash merges, commits to main | Preserves incremental TDD history, adds CI + preview per PR |

ADR: [adr/0017-toolchain.md](adr/0017-toolchain.md)

## 18. Design workflow
- **Chosen:** Claude Design canvases → `DESIGN.md` → shadcn build with frontend-design skill → Impeccable audit.
- **Alternatives:** Google Stitch; skip designs.
- **Why:** design before code; one AI toolchain; checkable anti-slop rules.
- ADR: [adr/0018-design-workflow.md](adr/0018-design-workflow.md)

## 18a. Pay-equity benchmark
- **Chosen:** compa-ratio = base ÷ **pay-band midpoint** (`pay_bands` per job role × level × country), plus a department rollup (median compa-ratio per department × country).
- **Rejected:** compa-ratio against the **peer-cohort median**, the first draft. It needs no extra table, but it's blind to systemic gaps: if a whole cohort is underpaid, its median moves with it.
- **Give up:** one more reference table to seed and maintain, and the seeded bands are synthetic. Real ACME bands would replace them ([03-clarifications.md](03-clarifications.md) Q15).

## 19. Known limitations we accept
- Static FX rates (illustrative).
- Single writer DB; serverless cold starts (~1–2 s).
- No SSO/MFA, no approval workflow, no scheduled raises.
- Free LLM tier limits and data-use caveat.
- Demo credentials public for the demo environment only.
