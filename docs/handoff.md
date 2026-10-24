# Handoff: build session → deployment session

- **Date:** 2026-10-24
- **Branch:** `claude/build-app-subagents-hxxp6x` (stands in for `main`; merge it into `main` with a merge commit, never squash)
- **State in one line:** the whole v1 app is built, reviewed and tested locally; the Turso database is created and loaded; **only the Vercel deploy and the submission remain.**

---

## 1. What is done

| Block | What was built | Evidence |
|---|---|---|
| B0 AI tooling | `CLAUDE.md` files, `.claude/` rules, skills (`/tdd`, `/commit`, …), reviewer agent, hooks (block lockfile/`.env` edits, guard risky Bash), `.mcp.json` | 145-check hook test harness `.claude/hooks/test-hooks.sh` |
| B1 Scaffold | uv + FastAPI factory, settings (production refuses weak secrets), problem+json errors, request id, Alembic, pytest fixtures; Next.js 16 + shadcn, ESLint/Prettier, Vitest + MSW, Playwright; Makefile, lefthook, `ci.yml` | `make verify` |
| B2 Domain | Money (integer minor units), FX to USD, half-even rounding, stats, pay equity (compa-ratio, flags, rollups), total comp | 100 % branch coverage |
| B3 Auth | Roles → permissions, argon2 + JWT cookie, login/logout/me, login lockout from audit events, authz matrix test over every route | |
| B4 Employees | Reference data, employees, append-only salary records, search/filter/sort/paging, optimistic locking, Viewer masking | |
| B5 Seed | Deterministic 10k employees (`--seed 42`), history, 1,360 pay bands, planted story; `make seed` ≈ 3 s | golden checksums |
| B6 Insights | Overview, by department, by job title, department cost, top earners, pay equity (cohorts, departments, drill-down), pay bands, FX rates; small-group rule + complementary suppression | DE Customer Success 0.93, only team below 0.95 |
| B7 Import/export | CSV + XLSX import (dry-run, all-or-nothing commit), template, CSV/XLSX export with role-aware columns and formula escaping | 10k-row dry-run ≈ 1 s |
| B8 Frontend | Login, app shell (phone bottom bar), insights, pay equity, employee directory/detail/salary change/create/edit/terminate, import, export, design per `docs/design/DESIGN.md` | Playwright smoke 10/10 at 1440 px and 390 px |
| B9 Ask about pay | 7 read-only tools, permission filtering, rate limit, FakeLLM tests for every row of docs/10 §10, `/ask` page, eval set | off without `LLM_API_KEY` |
| B10 Write-up | Root README, measured performance (docs/19 §9), prompt log | |
| Deploy prep | `backend/index.py` (Vercel entrypoint), `backend/.python-version` (3.13), root `vercel.json` (services), Turso DB loaded | API checked locally against Turso |

**Test totals:** 1,391 backend tests, 448 frontend tests, coverage gate 100 % on `domain/` and services, `make e2e` 10/10. The history has `test:` → `feat:` pairs (≈ 380 `test:` commits) and one merge commit per block. Every block got an independent review; the findings and fixes are in [ai/prompt-log.md](ai/prompt-log.md) entries 24–34.

---

## 2. Deployment state

| Item | State |
|---|---|
| Turso database | `incubyte-salary-assessment`, Mumbai (`aws-ap-south-1`), **created and loaded** (10,000 employees, 24,058 records, 39,570 components, 1,360 bands, 3 demo users) |
| Turso URL | `libsql://incubyte-salary-assessment-mugunthanbvn.aws-ap-south-1.turso.io` |
| Turso token | **Rotate it**: the first token was pasted in chat. Create a new one, revoke the old one, put only the new one in Vercel |
| Demo passwords | Already in the database; the user has them (not in the repo) |
| Vercel | **Not deployed yet** |

### 2.1 Vercel setup (one project, two services)

`vercel.json` at the repo root:

- `backend`: FastAPI, root `backend/`, entrypoint `index:app`, **public at `/api/*`** (it receives the full path, so routes stay `/api/v1/...`).
- `frontend`: Next.js, root `frontend/`, **public at `/*`**, binding `BACKEND_URL` → `backend`.
- `regions: ["bom1"]` (Mumbai, next to the database).

`BACKEND_URL` is the backend's **private** address, injected by Vercel at runtime for server-side fetches (`frontend/src/lib/api/origin.ts` `apiBaseUrl()`). The browser keeps calling `/api/v1/...` on the same domain, so the session cookie stays first-party.

### 2.2 Steps left (in order)

1. Merge the branch into `main` (merge commit).
2. Vercel → New Project → import the repo, **root directory = repo root**.
3. Environment variables (shared by both services):
   - `APP_ENV=production`
   - `DATABASE_URL=sqlite+libsql://incubyte-salary-assessment-mugunthanbvn.aws-ap-south-1.turso.io?secure=true`
   - `DATABASE_AUTH_TOKEN=<new Turso token>`
   - `JWT_SECRET=<32+ random bytes>` (e.g. `openssl rand -base64 48`)
   - `COOKIE_SECURE=true`, `CORS_ORIGINS=` (empty)
   - `NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS=true`
   - optional: `LLM_API_KEY` (Gemini) and `LLM_MODEL`
   - **do not set** `BACKEND_URL` (Vercel injects it) or `API_ORIGIN` (local only)
4. Deploy, then check: `https://<domain>/api/v1/health` → `"status":"ok"`; sign in as admin@, hr@, viewer@acme.example in **Chrome and Safari**; pages load data (proves the binding); the Viewer sees no salaries.
5. Put the live URL and demo credentials in the README; record deployed latency in [19-performance.md](19-performance.md) §9; tick [17-deployment.md](17-deployment.md) §7.
6. Optional: with a Gemini key, run `make eval-ask` and pin the model id.
7. Record the demo video ([demo-script.md](demo-script.md)), tag `v1.0.0`, reply to Incubyte's email.

**If the build fails**, likely causes: top-level `regions` not accepted in services mode (set the region in project settings instead), Python entrypoint detection, the `sqlalchemy-libsql` wheel, or the Python 3.13 pin. The fallback is in [ADR 0019](adr/0019-vercel-services-single-project.md): two projects, with `API_ORIGIN` set on the web project before its build.

---

## 3. Decisions taken (all logged; docs updated)

| Decision | Why | Where |
|---|---|---|
| The session branch stands in for `main` | The cloud session could push only there | prompt log 24 |
| Python 3.13, Node 22 | Installed in the build container; supported by Vercel | ADR 0017 |
| `git push` allowed in settings; force-push denied | An autonomous session can't answer a prompt per block | doc 16 §7 |
| Health check is read-only (`SELECT 1`) | The write check was only for the deferred deploy spike | doc 07 §3 |
| Statuses with no glossary slug use `type: about:blank` | RFC 9457 default | doc 07 §1.5 |
| SQLite transactions start with `BEGIN IMMEDIATE` | Concurrent read-then-write requests failed with "database is locked" | doc 06 §7 |
| Login lockout: 15-minute block from the 5th failure, re-checked after the password | Glossary rule; stops parallel bursts | doc 08 §9 |
| Salary range/sort only with one currency, one country or `salary_basis=usd` | Never compare amounts in different currencies | doc 07 §6.1 |
| `version` is null for callers without `SALARY_READ` | It revealed when someone's pay changed | doc 08 §4.1 |
| Complementary suppression over country ⊃ department ⊃ role ⊃ level, shared by all insight endpoints | Two reviewer attacks recovered one salary | doc 09 §2.8 |
| Viewers may filter insights by `status` | Aggregates only; small-group rule still applies | doc 09 §2.1 |
| Import commit allowed for the creator or a `USER_ADMIN` holder | Permissions, never role names | glossary §6 |
| Import: at most 500 stored errors, allowed values listed once per column | Stay under Vercel's 4.5 MB response limit | doc 11 |
| Ids allocated in Python for bulk inserts | Fast; documented as a SQLite/Turso-only assumption | docs 06 §8, 11 §5.6 |
| Seed noise narrowed (σ = 0.06, clipped) | Only the planted outliers are flagged | doc 12 §5, §8 |
| Ask outcome recorded as a second audit event `ask.answer` | Audit rows are append-only; burst-safe rate limit | doc 10 §9 |
| Phone navigation is a bottom bar; summaries are sentences, not tiles | DESIGN.md wins on look and feel | doc 13 §8 |
| Region Mumbai (`bom1` + `aws-ap-south-1`) | Incubyte is India-based | doc 17 §5 |
| Database name `incubyte-salary-assessment` | The user's choice | glossary §8 |
| One Vercel project with services instead of two projects | One domain, one deploy, private binding | ADR 0019 |
| DB loaded by batch copy, not row by row | Row-by-row over the network would take about an hour; batches took 79 s | doc 17 §6.1a |

---

## 4. Known limits and future work

- Ask has not run against a real model (no key in the build environment); the default model id `gemini-flash-latest` is unconfirmed; `make eval-ask` is pending.
- The whole-org pay-equity cohorts view is ≈ 500 ms p95 (budget 300 ms); the UI always asks for one country.
- Cross-endpoint suppression: combining different filters can still narrow a value (doc 09 §2.8).
- Cut from v1 (see [README](README.md) v1 scope): admin UI, raises and histogram insights, Postgres CI job, preview deployments, most e2e tests, Dependabot/CodeQL/knip.
- CI (`.github/workflows/ci.yml`) is in place but has not run on GitHub yet.
- `make e2e` uses fixed ports (3100, 8100) and a fixed temp DB path.

---

## 5. How to work on it

- Start: `make setup && make seed && make dev` → http://localhost:3000.
- Before saying done: `make verify` (and `make e2e` for UI changes).
- Rules: [CLAUDE.md](../CLAUDE.md) — test first, money never a float, permissions not roles, Conventional Commits, never `--no-verify` or force-push, never read `.env` files, never commit secrets.
- Prompt for the next session: start from §2.2 above.
