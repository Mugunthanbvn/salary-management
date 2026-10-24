# ACME Salary Management

A web app for ACME's HR manager to manage the pay of 10,000 employees in 10 countries. It keeps
each salary in its country's currency, shows pay insights in local currency and in USD, and checks
pay equity against salary bands. Admins and HR managers see salaries; Viewers see only safe
aggregates. Built with FastAPI and Next.js 16 as an Incubyte take-home, test first.

- **Live URL:** deployment pending (see [Deployment: pending](#deployment-pending))
- **Video demo:** not recorded yet

## Features (v1)

- **Employees and salary history:** create, edit, terminate and reactivate employees; every
  salary change appends a record (history is never edited); optimistic locking on edits.
- **Search, filter, sort:** by name, code or email, country, department, job role, level,
  employment type, status, currency and salary range; 25 per page.
- **Multi-currency insights:** headcount, payroll and pay statistics by country, department and
  job title, in each country's currency and converted to USD (with the FX date shown).
- **Band-based pay equity:** compa-ratio (base / band midpoint) per job role, level and country,
  plus a department rollup per country that shows team-wide gaps (for example the seeded
  DE Customer Success team at about 0.92).
- **Viewer masking and the small-group rule:** Viewers never see individual salaries, and any
  group with fewer than 5 people is hidden (with complementary suppression). Enforced in the API
  services, not the UI.
- **Import:** CSV or XLSX, up to 10,000 rows; a dry-run report first, then an all-or-nothing commit.
- **Export:** the filtered employee list as CSV or XLSX (salary columns only with `SALARY_READ`).
- **Ask about pay:** natural-language questions answered by read-only insight tools. It is
  switched off unless `LLM_API_KEY` is set.
- **Audit:** every change writes an audit event in the same transaction.
- **Deterministic seed:** 10,000 employees, about 24,000 salary records and 1,360 pay bands from
  `--seed 42`, with a planted demo story.

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/) (installs Python 3.13), Node 22 with corepack
(`corepack enable`), GNU Make and git.

```bash
make setup   # uv sync, pnpm install, git hooks, .env files from .env.example
make seed    # 10,000 employees into backend/dev.db (about 4 s)
make dev     # API on :8000, web app on :3000 (Ctrl-C stops both)
```

Open http://localhost:3000. API docs: http://localhost:8000/api/v1/docs.

### Demo accounts

| Role       | Email                 | Password               |
| ---------- | --------------------- | ---------------------- |
| Admin      | `admin@acme.example`  | `SEED_ADMIN_PASSWORD`  |
| HR manager | `hr@acme.example`     | `SEED_HR_PASSWORD`     |
| Viewer     | `viewer@acme.example` | `SEED_VIEWER_PASSWORD` |

The passwords come from the `SEED_*_PASSWORD` variables when you run `make seed`. The local
development defaults are in [backend/.env.example](backend/.env.example) (`change-me-admin`,
`change-me-hr`, `change-me-viewer`). Production refuses these defaults.

## Useful commands

| Command           | What it does                                                                      |
| ----------------- | --------------------------------------------------------------------------------- |
| `make verify`     | Lint, type-check, all tests with the coverage gate, `next build`, API drift check |
| `make test`       | Backend pytest (parallel) and frontend Vitest                                     |
| `make e2e`        | Playwright smoke flow on a seeded temporary database                              |
| `make api-sync`   | Export OpenAPI and regenerate the frontend's typed client                         |
| `make seed-turso` | Build `build/seed.db` for Turso (prints the upload command, never runs it)        |
| `make eval-ask`   | Run the Ask eval set against a real LLM (needs `LLM_API_KEY`)                     |
| `make help`       | List every target                                                                 |

## Architecture

```
Browser → Next.js 16 (frontend/) → /api rewrite → FastAPI (backend/) → SQLite locally / Turso in production
```

- The browser talks to one origin; Next.js rewrites `/api` to FastAPI, which sets an HttpOnly
  session cookie. FastAPI is the only authority for data and permissions; the UI only hides.
- Backend layers: router → service → repository → model. Services own transactions, masking,
  the small-group rule and audit writes. `domain/` (money, currency, stats, pay equity) is pure.
- Money is integer minor units plus an ISO 4217 code, never a float; rounding is half-even.
- Details: [docs/05-architecture.md](docs/05-architecture.md) and
  [docs/06-data-model.md](docs/06-data-model.md).

## Testing

- **TDD in the history:** each behaviour has a `test:` commit before its `feat:` commit
  (`git log --oneline`: 335 `test:` and 239 `feat:` commits so far).
- **Backend:** 1,270 pytest tests (unit + integration on in-memory SQLite), including an
  authorization matrix over every endpoint and role. 99 % overall coverage; a gate fails the
  build below 90 % branch coverage on `domain/` and the services (currently 100 %).
- **Frontend:** 362 Vitest tests over 44 files.
- **End to end:** one Playwright smoke flow (`make e2e`).
- Performance numbers on the 10k seed: [docs/19-performance.md](docs/19-performance.md) §9.
- Strategy: [docs/14-testing-strategy.md](docs/14-testing-strategy.md).

## Documentation

- [docs/README.md](docs/README.md): index and the v1 scope (what was cut and why).
- [docs/glossary.md](docs/glossary.md): canonical names, enums, numbers and error codes.
- [docs/adr/](docs/adr/): architecture decision records.
- [docs/ai/prompt-log.md](docs/ai/prompt-log.md): how AI was used, with the real prompts.
- [docs/20-trade-offs.md](docs/20-trade-offs.md): the main choices against their alternatives.

## Not done / future work

- **Admin UI** (users, FX rates, countries, audit log viewer): users, rates and countries are
  seeded; audit events are written and tested but have no screen.
- **Raises insight and the salary distribution histogram:** not built.
- **Postgres CI job:** CI runs on SQLite only.
- **Preview deployments:** production only.
- **Most Playwright tests:** only one smoke flow; the rest is covered by API and component tests.
- **Dependabot, CodeQL, knip:** not set up.
- **Ask evals:** the eval set exists, but a run against a real model is pending until a key is
  available. The exact Gemini model id is not confirmed yet (`LLM_MODEL` is empty by default).
- **Cross-endpoint suppression limit:** the small-group rule protects totals shown under the same
  filters. Combining different filters or endpoints whose populations differ can still narrow a
  value down ([docs/09](docs/09-insights-pay-equity.md) §2.8).
- **Ids allocated in Python** (`max(id) + 1`) by the import commit and the seed work on SQLite and
  Turso only: a move to Postgres needs a `setval` after them. On Turso, two imports committing at
  the same moment can clash; the later one rolls back and is retried by the user
  ([docs/11](docs/11-import-export.md) §5.6).
- **Import is create-only:** no upsert of existing employees.
- **Pay-equity cohorts view** returns all ~1,200 cohorts in one response and is over its latency
  budget locally ([docs/19](docs/19-performance.md) §9); paging or a summary-first view would fix it.

## Deployment: pending

The target is Vercel (two projects) plus Turso, in one region
([docs/17-deployment.md](docs/17-deployment.md), [ADR 0016](docs/adr/0016-deploy-vercel-turso.md)).
Remaining steps:

1. Build the database file with real demo passwords:
   `SEED_ADMIN_PASSWORD=… SEED_HR_PASSWORD=… SEED_VIEWER_PASSWORD=… make seed-turso`.
2. Create the Turso database from it (same region as the API, US-East by default):
   `turso db create salary-prod --from-file build/seed.db`, then create an auth token
   ([docs/17](docs/17-deployment.md) §6.1).
3. Create the Vercel project `salary-api` from `backend/` and set its env vars: `APP_ENV=production`,
   `DATABASE_URL` (Turso URL, no token), `DATABASE_AUTH_TOKEN`, `JWT_SECRET` (32+ random bytes),
   `COOKIE_SECURE=true`, empty `CORS_ORIGINS`, and optionally `LLM_BASE_URL`, `LLM_MODEL`,
   `LLM_API_KEY`. Put the function in the database's region.
4. Create the Vercel project `salary-web` from `frontend/` with `API_ORIGIN` set to the
   `salary-api` URL (set before `next build`, so `/api` is rewritten to it) and
   `NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS=true` on the demo deployment.
5. Verify: `GET /api/v1/health` answers through the web URL, and sign-in works for all three
   roles in **Chrome and Safari** (the session cookie must survive the rewrite). Then work through
   the checklist in [docs/17](docs/17-deployment.md) §7 and record the deployed numbers in
   [docs/19](docs/19-performance.md) §9.
