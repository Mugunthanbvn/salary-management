# ACME Salary Management

Salary management for ACME's HR manager: 10,000 employees in 10 countries, multi-currency insights,
band-based pay equity, role-based masking. An Incubyte take-home: **quality over breadth**, TDD visible in git history.

## Architecture

```
Browser → Next.js 16 (frontend/) → /api rewrite → FastAPI (backend/) → SQLite locally / Turso in production
```

- Backend `backend/src/salary_api/`: `core/` (config, db, security, permissions, deps, errors, logging),
  `domain/` (money, currency, stats, pay_equity: pure, no I/O), `modules/<feature>/`
  (auth, reference, employees, salaries, insights, imports, exports, audit, ask), `seed/`.
- Frontend `frontend/src/`: `app/` (login, insights, pay equity, employees, import, ask),
  `lib/api/` (generated types + typed client), `lib/money.ts`, `components/`, `proxy.ts`.
- Details: [docs/05-architecture.md](docs/05-architecture.md) §5–§6, [docs/06-data-model.md](docs/06-data-model.md).
- Runtimes: Python 3.13 (uv), Node 22 (pnpm via corepack).

## Commands

Use make targets, not ad-hoc commands.

| Command | Use |
|---|---|
| `make setup` | Install everything once after clone (uv sync, pnpm install, lefthook, `.env` from `.env.example`) |
| `make dev` | API on :8000 and web on :3000, local SQLite `backend/dev.db` |
| `make migrate` | `alembic upgrade head` |
| `make seed` | Deterministic 10k employees (`--seed 42`) |
| `make seed-turso` | Build `build/seed.db` for Turso (prints the command; never calls Turso) |
| `make fmt` / `make lint` / `make typecheck` | ruff + prettier / ruff + eslint + prettier check / pyright + tsc |
| `make test` | Backend pytest (parallel, coverage) + frontend Vitest |
| `make e2e` | Playwright smoke flow on a seeded temp DB |
| `make api-sync` | Export OpenAPI → regenerate `frontend/src/lib/api/schema.d.ts` → `tsc` |
| `make verify` | lint + typecheck + test + API drift check: run before saying "done" |
| `make eval-ask` | Ask eval set against a real LLM (manual, needs `LLM_API_KEY`) |
| `make clean` | Remove venv, node_modules, build output, local DBs |

Fastest TDD loop: `cd backend && uv run pytest tests/unit/domain -q` or `cd frontend && pnpm vitest`.

## Non-negotiables

- **Test first.** No production code without a failing test. Use `/tdd`.
- **Money is never a float.** Integer minor units + ISO 4217 code; `Decimal` only for rates and ratios;
  rounding is half-even. Every salary is in its country's currency. See `.claude/rules/money.md`.
- **Layering:** router → service → repository → model. Routers hold no business logic;
  repositories hold no business rules. The service method is the transaction boundary.
- **Check permissions, never role names:** `require_permission(Permission.SALARY_READ)`.
- **Masking and the small-group rule (`MIN_GROUP_SIZE = 5`) live in services**, not routers or the UI.
- **No business logic in Next.js.** FastAPI is the only authority for data and permissions; the UI only hides.
- **Every mutation writes its audit event** (names in [docs/glossary.md](docs/glossary.md) §4) in the same transaction.
- **Salary history is append-only.** Never update or delete `salary_records`.
- **Errors are RFC 9457 problem+json** with the glossary §5 slugs and statuses.
- **Never edit generated files or lockfiles by hand** (`schema.d.ts`, `openapi.json`, `uv.lock`, `pnpm-lock.yaml`)
  and never read or edit `.env` files. Hooks block this. Use `uv add`, `pnpm add`, `make api-sync`.
- **Every screen works at 390 px** (fully mobile responsive, [docs/13-frontend-ux.md](docs/13-frontend-ux.md) §8).
- **Small Conventional Commits**, `test:` before `feat:`. Use `/commit`.
- **Log material AI interactions** with `/log-prompt`.

## Commits

`type(scope): subject`, subject ≤ 72 chars, imperative. Types: feat, fix, test, refactor, docs, chore, ci,
build, perf, style, revert. Scopes follow modules (money, auth, employees, salaries, insights, import, export,
audit, ask, seed, ui, deploy, docs). Every commit message ends with the attribution trailer lines the
current session provides (e.g. in its system instructions). If it provides none, end with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never copy a session link from an old commit.

Never `--no-verify`, never force-push, never amend a pushed commit.

## Definition of done

[docs/14-testing-strategy.md §11](docs/14-testing-strategy.md#11-definition-of-done-for-any-story):
tests written first, `make verify` green, new endpoints in the authz matrix, mutations audited,
client regenerated, docs updated. Run `/verify` before claiming done; use the `reviewer` agent before merging a block.

## Where the docs live

- [docs/README.md](docs/README.md): index and the **v1 scope** table (what is cut: admin UI, raises,
  histogram, Postgres CI job, Groq, Dependabot/CodeQL/knip, previews, most Playwright tests).
- [docs/glossary.md](docs/glossary.md): canonical names, enums, numbers, errors, env vars. **It wins over every other doc.**
- [docs/adr/](docs/adr/): decisions. When a decision changes, write a new ADR with `/adr`; don't silently diverge.
- [docs/18-implementation-plan.md](docs/18-implementation-plan.md): build blocks B0–B10.

## When unsure

Ask the user when a requirement is unclear. In an autonomous session (the user delegated decisions),
decide with the precedence rule — glossary > docs/README v1 scope > the specific doc > the simplest
consistent option — apply it, update the affected doc, and log it in docs/ai/prompt-log.md (an ADR if architectural).
