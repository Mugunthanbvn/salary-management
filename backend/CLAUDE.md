# Backend (FastAPI)

Loaded when working under `backend/`. Root rules in [../CLAUDE.md](../CLAUDE.md) still apply.

## Stack

Python 3.13, uv, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2.x (sync), Alembic,
pwdlib[argon2], PyJWT, openpyxl, structlog. Quality: ruff (lint + format), Pyright strict on `src/`,
pytest + hypothesis + time-machine + pytest-randomly + pytest-xdist + pytest-cov.

## Layout

```
src/salary_api/
  main.py          app factory: routers, problem+json handlers, request-id middleware
  core/            config, db, security, permissions, deps, errors, logging
  domain/          money, currency, stats, pay_equity (stdlib only, no I/O)
  modules/<feature>/{router,schemas,service,repository,models}.py
  seed/            deterministic generator + CLI
tests/unit/        no DB (domain, permissions, parsers, csv safety)
tests/integration/ TestClient + in-memory SQLite; test_authz_matrix.py covers every endpoint × role
tests/factories.py plain builder functions (make_employee, make_salary_record, ...)
```

New feature slice: use `/new-module`. Mirror an existing module; don't invent a new pattern.

## Rules

- **Dependencies:** `uv add <pkg>`, `uv add --group test <pkg>`, `uv remove <pkg>`. Never edit `uv.lock`.
- **Layers:** routers import schemas, services and `core.deps` only. Services own use cases, transactions,
  masking, the small-group rule and audit writes. Repositories run SQLAlchemy queries only. Domain is pure.
- **DB:** SQLAlchemy expressions only; never raw SQL strings with interpolation. Sort fields come from an allow-list.
  The DB is chosen only by `DATABASE_URL` (+ `DATABASE_AUTH_TOKEN` via `connect_args`); `NullPool` in production.
- **Validation:** request models use `extra="forbid"`; enums from the glossary; caps from the glossary §3.
- **Errors:** raise domain exceptions; the handlers in `core/errors.py` map them to RFC 9457 problem+json.
  Services never import FastAPI `Request`/`Response` or status codes.
- **Migrations:** every model change gets an Alembic revision
  (`uv run alembic revision --autogenerate -m "<what>"`). Review the generated file by hand.
- **Logging:** structlog JSON with `request_id`. Never log secrets, tokens, passwords or full salary rows.
- **After any router or schema change:** run `make api-sync` (see `/api-sync`).

## Tests

- In-memory SQLite (`StaticPool`, `PRAGMA foreign_keys=ON`), each test in a rolled-back transaction.
- Freeze time with `time-machine` (default `2026-10-01T09:00:00Z`). Seeded `random.Random(seed)`, never global `random`.
- No network. The LLM goes through `FakeLLM`.
- Names read like requirements: `test_viewer_cannot_see_individual_salary`.
- Coverage gate: ≥ 90 % branch coverage on `domain/` and `modules/*/service.py`.
- While iterating, run the single fastest relevant test: `uv run pytest tests/unit/domain -q`
  or `uv run pytest -k <name> -q`. Before done: `make verify` from the repo root.
