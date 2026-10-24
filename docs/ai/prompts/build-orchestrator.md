# Prompt: build the whole app with an orchestrator and subagents

Paste everything below the line into a new Claude Code session opened at the repository root.

---

You are the **lead engineer and orchestrator** for this repository: ACME Salary Management, an Incubyte take-home (Software Craftsperson, Python/React/AI). Your job is to take the repo from "docs only" to a **complete, working, tested app running locally**, by planning the work and delegating it to subagents. **Deployment is out of scope for this session**: do not run any Vercel, Turso or other cloud command; leave deployment as the only pending item.

## 1. Read before doing anything

Read these yourself (not via a subagent), in this order, and keep them as your source of truth:

1. `docs/README.md`: the **v1 scope** table (what is cut) and the decision log.
2. `docs/glossary.md`: canonical names, enums, audit actions, error codes, env vars, numbers. **It wins over every other doc.**
3. `docs/00-assessment-brief.md` and `docs/02-requirements-one-pager.md`: what is graded.
4. `docs/18-implementation-plan.md`: the build blocks B0–B10, their tasks, done-criteria and the B6 privacy checklist.
5. `docs/14-testing-strategy.md`: TDD workflow, test layout, determinism, coverage gate, definition of done.
6. Skim, then give the relevant sections to each subagent: `05-architecture`, `06-data-model`, `07-api-spec`, `08-security-rbac`, `09-insights-pay-equity`, `10-ai-ask-design`, `11-import-export`, `12-seed-data`, `13-frontend-ux` (§8 is fully mobile responsive), `15-tooling-devex`, `16-claude-code-setup`, `docs/design/DESIGN.md` and the reference screens in `docs/design/claude/`.

Precedence when docs disagree: glossary > README v1 scope > the specific doc > the simplest option consistent with the rest.

## 2. How you work

- **You orchestrate; subagents build.** You keep the plan, the integration and the quality bar. Give each subagent one block (or one clearly separated half of a block) with a self-contained brief (template in §5). Don't do large implementation work yourself; do integration, merges and fixes between blocks.
- **Order.** B0 → B1 → B2 → B3 → B4 → B5 → then B6 and B7 (may run in parallel in separate git worktrees, `isolation: "worktree"`, because they touch different modules; you merge them) → B8 → B9 → B10 (everything except deployment). The frontend (B8) may be split across two or three subagents by screen once the shell, API client and `lib/money.ts` exist.
- **Never stop to ask the user.** When something is unclear, decide using the precedence rule, prefer the simplest choice that keeps the docs consistent, and record it: a short entry in `docs/ai/prompt-log.md` (what was unclear, what you chose, why), plus a new ADR via the `docs/adr/0000-template.md` format if it is an architectural change. Update the affected doc in the same commit so docs and code never disagree. The only acceptable reason to stop is something that needs a human credential, and even then finish everything else first and list it in the final report.
- **Keep your own context lean.** Ask subagents for a short report (what was built, tests added, commands run with results, decisions made, open issues), not file dumps.

## 3. Non-negotiables (put these in every subagent brief)

- **TDD, visible in history.** For every behaviour: write one failing test, run it and confirm it fails for the right reason, commit `test(<scope>): …`; write the minimum code, run the suite, commit `feat(<scope>): …`; refactor on green, commit `refactor(<scope>): …` if anything changed. Bug fixes start with `test: reproduce …`. Commits are made as the work happens, never split or rewritten afterwards. Conventional Commits, subject ≤ 72 chars, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Tests are fast and deterministic**: in-memory SQLite, frozen time (time-machine), seeded randomness, no network (FakeLLM for Ask). Coverage ≥ 90 % on `domain/` and `modules/*/service.py`.
- **Money** is integer minor units + ISO 4217 code, never a float; `Decimal` only for FX, ratios and rounding (half-even). Every salary is in its country's currency.
- **Layering**: router → service → repository → model; permissions checked by permission name, never role name; masking and the small-group rule (`MIN_GROUP_SIZE = 5`) live in services; every mutation writes its audit event (glossary §4 names) in the same transaction.
- **Errors** are RFC 9457 problem+json with the glossary §5 slugs and statuses.
- **Frontend**: Next.js 16 App Router, TypeScript strict, shadcn/ui restyled to `docs/design/DESIGN.md` ("Marked-up printout"), types generated from OpenAPI (`make api-sync`), no business logic or money arithmetic in Next.js, login and uploads via client `fetch` through the `/api` rewrite (never a Server Action), `proxy.ts` excludes `/api` and `/login`, **every screen fully usable at 390 px** (13 §8).
- **Never** edit lockfiles or generated files by hand, read `.env` files, use `--no-verify`, force-push, or run deploy/cloud commands.

## 4. Block-by-block notes

- **B0**: create the AI tooling described in `16-claude-code-setup.md` (root/backend/frontend `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` with permissions and hooks, `.claude/rules/*`, `.claude/skills/*` incl. `/tdd` and `/commit`, `.claude/agents/reviewer.md`, `.mcp.json`), trimmed to the v1 scope. Skip the Stitch/Claude Design and Impeccable steps.
- **B1**: scaffold backend (uv, FastAPI app factory, pydantic-settings, problem+json handler, request-id middleware, Alembic, ruff, pyright strict, pytest) and frontend (create-next-app, shadcn, ESLint + Prettier, Vitest + RTL + MSW, Playwright), root Makefile (targets in 15 §6 that are in scope), lefthook, `.editorconfig`, `.gitignore`, `.env.example` files, `.python-version` (a version Vercel supports: 3.12–3.14; prefer 3.13), one `ci.yml` (backend, frontend, contract drift, gitleaks). **Skip the deploy spike**, but keep the app deploy-ready: DB chosen only by `DATABASE_URL` (+ `DATABASE_AUTH_TOKEN` via `connect_args`), `NullPool` when `APP_ENV=production`, `/api/v1/health`, the `next.config.ts` rewrite to `API_ORIGIN`.
- **B2–B5**: as in the plan. Employees and salary records are built together (an employee is created with its `HIRE` record in one transaction). Seed exactly 10,000 employees deterministically with the planted demo story; `make seed` must be fast locally. `make seed-turso` may build the seed file but must not call Turso.
- **B6**: implement the insight endpoints in scope and **all four items of the B6 privacy checklist** (Viewer gets `min`/`max` as null; differences computed from suppressed values; complementary suppression; no compa-ratio for non-full-time), each with a test.
- **B7**: CSV **and** XLSX import (dry-run → all-or-nothing commit) and CSV/XLSX export, per `11-import-export.md`; insert with IDs pre-allocated in Python.
- **B8**: all v1 screens: login, insights, pay equity (with drill-down), employee directory, employee detail + record salary change, create/edit/terminate, import, export, Ask page; role-aware UI (Viewer sees no individual pay). Use `docs/design/claude/*.dc.html` as the visual reference. One Playwright smoke flow (HR login → search → record raise) at 1440 px and 390 px.
- **B9**: Ask about pay with the OpenAI-compatible adapter (Gemini default), FakeLLM tests for every row of `10-ai-ask-design.md` §10, the feature disabled when `LLM_API_KEY` is empty. Write `docs/ai/evals/ask.yaml` with about 5 cases; run `make eval-ask` only if a key is present in the environment, otherwise note it as pending.
- **B10 (minus deployment)**: root `README.md` (what it is, how to run locally with `make setup && make dev`, demo accounts from env, architecture summary, link to `docs/`, an honest "Not done / future work" section, and a **"Deployment: pending"** section pointing to `docs/17-deployment.md` §7), update `docs/19-performance.md` with local measurements (seed time, p95 of main endpoints at 10k), finish the prompt log. Do not tag a release.

## 5. Subagent brief template

Give every subagent a brief like this (fill in the angle brackets):

```
You are implementing <block and goal> in the ACME Salary Management repo.
Read first: docs/glossary.md (wins over other docs), <exact doc sections>, docs/14-testing-strategy.md §2 and §4.
Scope: <files/modules you own>. Do not change: <other modules>, lockfiles by hand, generated files.
Behaviours to build, in this order, each test-first: <list from the plan / API spec>.
Rules: <paste §3 non-negotiables>.
Work on branch <bNN-slug> created from main. Commit test → feat → refactor as you go.
Before finishing: run `make verify` (lint, typecheck, tests, coverage) and fix everything until green.
If something in the docs is unclear: choose the simplest option consistent with the glossary, apply it, update the doc, and list the decision in your report.
Report back in ≤ 20 lines: what you built, tests added (count) and their result, commands you ran and their results, decisions made, anything left open.
```

## 6. After each block

1. Read the subagent's report. If `make verify` isn't green, send it back (or fix it yourself if small).
2. Get an independent review: spawn a fresh reviewer subagent (or the `.claude/agents/reviewer.md` agent) with only the branch diff and the checklist in `16-claude-code-setup.md` §6, without your conclusions. Fix every real finding test-first.
3. Merge the branch into `main` with `git merge --no-ff` (never squash), run `make verify` on `main`, then `git push origin main` and push the branch.
4. Add a prompt-log entry for any material decision or AI correction.

## 7. Definition of done for this session

- `make setup && make dev` starts the API and the web app locally on SQLite; `make seed` loads 10,000 employees.
- Every v1 feature in `docs/02-requirements-one-pager.md` (as cut by the README v1 scope) works in the browser for HR Manager, Admin and Viewer, at desktop and phone width.
- `make verify` is green on `main`; coverage gate met; the Playwright smoke passes locally; CI config is present.
- The commit history shows `test:` → `feat:` pairs for every block, merged with merge commits.
- Docs match the code; every decision you made is in the prompt log or an ADR.
- **Only deployment is pending.** Finish with a short report: what was built, test counts and coverage, decisions you made, known limitations, and the exact remaining deployment steps (from `docs/17-deployment.md` §6–§7).
