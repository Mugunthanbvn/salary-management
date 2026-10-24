# ACME Salary Management

A web app for ACME's HR team to manage the salaries of 10,000 employees in 10 countries, with
currency-correct insights and band-based pay equity. An Incubyte take-home: FastAPI + Next.js 16.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs Python 3.13 from `.python-version` if needed)
- Node 22 (`.nvmrc`) with pnpm through corepack (`corepack enable`)
- GNU Make and git

## Quick start

```bash
make setup   # uv sync, pnpm install, git hooks, .env files from .env.example
make dev     # migrations, then the API on :8000 and the web app on :3000 (Ctrl-C stops both)
```

Open http://localhost:3000. API docs: http://localhost:8000/api/v1/docs.
The local database is the SQLite file `backend/dev.db`: no Docker, no cloud account.

## Checks

```bash
make verify  # lint, type-check, tests + coverage gate, next build, API drift check
make help    # every target
```

## Documentation

Start at [docs/README.md](docs/README.md) (v1 scope, design, decisions).
Canonical names and values are in [docs/glossary.md](docs/glossary.md).
