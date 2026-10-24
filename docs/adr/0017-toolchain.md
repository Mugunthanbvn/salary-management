# ADR-0017: Development toolchain (type checking, linting, git hooks, dependency updates, API client)

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The candidate asked for an industry-standard setup using the latest tools, researched rather than assumed. Several categories had real contenders in October 2026. Exact versions are resolved at scaffold time (`uv add`, `pnpm add`) and pinned by lockfiles. The full tool-by-tool explanation is in [15-tooling-devex.md](../15-tooling-devex.md).

## Decision drivers

- Correctness signal in CI; the same results in the editor (VS Code) and CI.
- Monorepo friendliness (Python + Node).
- Maturity over novelty for gating checks.
- Low noise in the commit history.

## Decisions and alternatives

### 1. Python type checker → **Pyright (strict on `src/`)**
| Option | Notes |
|---|---|
| **Pyright** ✅ | About 98% typing-spec conformance in third-party comparisons; same engine as VS Code Pylance, so editor = CI; fast |
| mypy | Mature, best plugin ecosystem, but slower and about 58% conformance |
| ty (Astral) | Fastest, but **beta** (0.0.x as of Oct 2026); good as a second opinion, not a gate |
| Pyrefly (Meta) | Reached 1.0 in May 2026; promising but newer, and lacks the gradual guarantee |

### 2. JS/TS linting and formatting → **ESLint (flat config) + Prettier**
| Option | Notes |
|---|---|
| **ESLint + Prettier** ✅ | `eslint-config-next`, `typescript-eslint` (type-aware), `react-hooks`, `jsx-a11y`; Prettier + tailwind class sorting |
| Biome 2 | Much faster, one tool, but **no confirmed parity** with the Next.js and react-hooks rules |

Note: **Next.js 16 removed `next lint`**, and `next build` no longer lints, so CI runs ESLint explicitly.

### 3. Git hooks → **lefthook**
| Option | Notes |
|---|---|
| **lefthook** ✅ | Single binary, parallel, **monorepo-aware** (`root` per command, staged files only) |
| pre-commit | Huge hook catalogue, but poor subdirectory/monorepo support, and uv needs a plugin |
| prek | Rust drop-in for pre-commit with workspace mode; newer |
| husky + lint-staged | Node-centric; awkward for the Python half |

### 4. Dependency updates → **Dependabot** (uv, npm, github-actions; grouped, monthly)
| Option | Notes |
|---|---|
| **Dependabot** ✅ | Built into GitHub, zero install, supports uv lockfiles (some gaps tracked upstream) |
| Renovate | Stronger uv lockfile maintenance and grouping, but needs an app install and creates more PR noise in a history reviewers will read |

### 5. API client generation → **openapi-typescript + openapi-fetch**
See [ADR-0014](0014-contract-first-openapi-client.md). Alternatives: Hey API (full SDK + Zod + TanStack plugins), Orval (hooks + mocks), Kubb. All generate more than this project needs.

### Other choices (uncontested)
- **uv** for Python packaging, environments and lockfiles (dependency groups `dev` for tools and tests, `seed` for Faker).
- **ruff** for Python lint + format (rules E, F, I, B, UP, SIM, S, PT, RUF, N, PL).
- **pytest** + pytest-cov (90% gate on domain + services) + hypothesis + pytest-randomly + pytest-xdist + time-machine.
- **pip-audit**, **gitleaks**, **CodeQL** for security.
- **Vitest 4 + React Testing Library + jsdom + MSW**, and **Playwright** for e2e.
- **knip** for unused files, exports and deps.
- **Root Makefile** as the single command entry point.
- **pnpm** via corepack; **Node 22 LTS**; **Python 3.13** (versions Vercel supports and the ones in the build environment).
- Libraries: **pwdlib[argon2] + PyJWT** (FastAPI docs moved off passlib and python-jose); **SQLAlchemy 2.1** (2.1 final was out at scaffold time).

## Resolved versions (backend)

Installed with `uv add` at scaffold time (2026-10-24) and pinned in `backend/uv.lock`. Later updates change the lockfile, not this list.

| Group | Packages |
|---|---|
| Runtime | Python 3.13, uv 0.11 |
| App | fastapi 0.162.0 (starlette 1.9.0), uvicorn[standard] 0.54.0, pydantic 2.14.1, pydantic-settings 2.16.1, sqlalchemy 2.1.6, alembic 1.20.1, pwdlib[argon2] 0.3.1 (argon2-cffi 25.1.0), pyjwt 2.15.1, python-multipart 0.0.32, openpyxl 3.1.5, openai 3.37.0, structlog 26.1.0, sqlalchemy-libsql 0.2.0 (Turso dialect; libsql-experimental 0.0.55) |
| dev | ruff 0.17.2, pyright 1.1.414, pytest 9.1.1, pytest-cov 7.1.0 (coverage 7.17.0), hypothesis 6.170.9, pytest-randomly 5.0.0, pytest-xdist 3.8.0, pytest-socket 0.8.1, time-machine 3.5.1, httpx 0.28.1, lefthook 2.2.2 (the PyPI package that ships the binary) |
| seed | faker 40.43.0 |

## Resolved versions (frontend)

Installed with `pnpm create next-app@16.4.3` and `pnpm add` at scaffold time (2026-10-24), pinned in `frontend/pnpm-lock.yaml`.

| Group | Packages |
|---|---|
| Runtime | Node 22, pnpm 10.28.0 (via corepack, `packageManager`) |
| App | next 16.4.3 (Cache Components on), react 19.3.0, tailwindcss 4.3.3, shadcn 4.22.1 (radix base), openapi-fetch 0.17.0 |
| Dev | typescript 5.9.3, eslint 9.39.5, typescript-eslint 8.72.0, prettier 3.9.10, vitest 4.1.12, vite 8.3.5, jsdom 30.1.3, msw 2.15.0, @playwright/test 1.63.0 (pinned to the pre-installed browsers), openapi-typescript 7.13.0 |

The Turso dialect (`sqlite+libsql://`) is installed, and a test builds a production engine from that URL without connecting. Talking to a real Turso database is still checked at deploy time ([17-deployment.md](../17-deployment.md)).

## Consequences

### Positive
- Mature gates, consistent editor and CI feedback, a clean monorepo hook setup, minimal PR noise.

### Negative / risks
- Two linters and formatters (ruff for Python, ESLint/Prettier for TS) instead of one universal tool.
- Pyright strict on SQLAlchemy/Pydantic code may need a few targeted `# pyright: ignore[...]` comments with justification.
- Tool versions move fast. Lockfiles pin them, and Dependabot proposes updates monthly.

## Links

- [15-tooling-devex.md](../15-tooling-devex.md), [14-testing-strategy.md](../14-testing-strategy.md), [04-research.md](../04-research.md)
