# 16 — Claude Code Project Setup

How the repository configures Claude Code: memory files, rules, skills, the reviewer agent, permissions, hooks and MCP servers. The goal is AI assistance that follows our engineering standards **by construction**, not by hoping.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [ai/workflow.md](ai/workflow.md) · [ai/prompt-log.md](ai/prompt-log.md) · [14-testing-strategy.md](14-testing-strategy.md) · [15-tooling-devex.md](15-tooling-devex.md) · [13-frontend-ux.md](13-frontend-ux.md) · [08-security-rbac.md](08-security-rbac.md) · [adr/0017-toolchain.md](adr/0017-toolchain.md) · [adr/0018-design-workflow.md](adr/0018-design-workflow.md)

---

## 1. Why commit the AI setup

The brief asks us to "use AI intentionally while maintaining correctness and quality" and to commit "prompts or instructions used with AI tools". Incubyte describes AI as an amplifier of engineering discipline, where "the test defines done". Committing the Claude Code configuration makes that discipline **inspectable**:

- Reviewers can read exactly which rules the AI was held to (CLAUDE.md, `.claude/rules/`).
- Repeatable procedures (TDD loop, ADRs, API sync) are encoded as skills rather than retyped prompts.
- **Hooks and permissions enforce** what text instructions can only request, e.g. never hand-editing a lockfile and never reading `.env`.
- The prompt log records where the AI was wrong and how it was corrected ([ai/prompt-log.md](ai/prompt-log.md)).

Instruction text is advisory and hooks are deterministic. So rules that can be enforced mechanically live in hooks or `settings.json`, and CLAUDE.md stays short (< 200 lines), following Anthropic's published best practice.

## 2. File map

```
CLAUDE.md                      # root project memory (always loaded)
AGENTS.md                      # pointer for other AI tools
backend/CLAUDE.md              # loaded when working under backend/
frontend/CLAUDE.md             # loaded when working under frontend/
.mcp.json                      # project MCP servers (Context7, Playwright)
.claude/
  settings.json                # permissions + hooks (committed, shared)
  settings.local.json          # personal overrides (git-ignored)
  rules/
    money.md  testing.md  security.md  api-contract.md  design.md
  skills/
    tdd/SKILL.md  adr/SKILL.md  verify/SKILL.md  api-sync/SKILL.md
    log-prompt/SKILL.md  new-module/SKILL.md  commit/SKILL.md
  agents/
    reviewer.md
  hooks/
    block-protected-files.sh   # PreToolUse guard (Read/Edit/Write)
    guard-bash.sh              # PreToolUse guard (Bash)
    format-changed-file.sh     # PostToolUse formatter
    test-hooks.sh              # tests for the hooks: .claude/hooks/test-hooks.sh
```

---

## 3. Memory files

### 3.1 Root `CLAUDE.md` (outline, < 200 lines)

1. **Purpose**: two lines: salary management for ACME's HR manager; Incubyte assessment; quality over breadth.
2. **Architecture map**: one diagram line (`Next.js → /api rewrite → FastAPI → SQLite/Turso`) and the module list, with links to [05-architecture.md](05-architecture.md) and [06-data-model.md](06-data-model.md).
3. **Commands**: `make setup | dev | test | verify | api-sync | seed | e2e`. Use make targets, not ad-hoc commands.
4. **Non-negotiables**:
   - **Test first.** Never write production code without a failing test; use `/tdd`.
   - **Money is never a float.** Integer minor units + ISO 4217 code; `Decimal` only for rates and ratios. See `.claude/rules/money.md`.
   - **Layering:** router → service → repository → model. Routers hold no business logic; repositories hold no business rules.
   - **Check permissions, not role names** (`require_permission(Permission.SALARY_READ)`).
   - **No business logic in Next.js.** FastAPI is the single authority for data and permissions; the UI only hides.
   - **Mutations write audit events** in the same transaction.
   - **Salary history is append-only**; never update or delete `salary_records`.
   - **Never edit generated files or lockfiles by hand** (`schema.d.ts`, `uv.lock`, `pnpm-lock.yaml`). Hooks block this.
   - **Small Conventional Commits**, with `test:` before `feat:`.
   - **Log material AI interactions** with `/log-prompt`.
5. **Definition of done**: links to [14-testing-strategy.md](14-testing-strategy.md#11-definition-of-done-for-any-story).
6. **Where the docs live**: the docs index, the ADRs, and "when a decision changes, write a new ADR (`/adr`), don't silently diverge".
7. **When unsure**: ask the user. Don't assume requirements (the brief explicitly says "Ask questions — don't assume").

### 3.2 `backend/CLAUDE.md` (outline)

- Stack: Python 3.14, uv, FastAPI, Pydantic v2, SQLAlchemy 2.x (sync), Alembic, Pyright strict, ruff.
- Module slice convention: `modules/<feature>/{router,schemas,service,repository,models}.py`; use `/new-module`.
- Dependencies via `uv add` / `uv add --group test` only.
- DB: never use raw SQL strings with interpolation. Use SQLAlchemy expressions. Sort columns come from an allow-list.
- Errors: raise domain exceptions; the handlers map them to RFC 9457 problem+json.
- Tests: `tests/unit` (no DB), `tests/integration` (TestClient). Factories in `tests/factories.py`. Freeze time with `time-machine`. No network.
- Migrations: every model change gets an Alembic revision; review the autogenerate output by hand.
- Run the single fastest relevant test while iterating: `uv run pytest tests/unit/domain -q`.

### 3.3 `frontend/CLAUDE.md` (outline)

- Stack: Next.js 16 App Router, React 19, TS strict, Tailwind v4, shadcn/ui, TanStack Table, react-hook-form + zod, nuqs, openapi-fetch.
- Data fetching: Server Components call the API through `lib/api/server.ts` (cookie forwarded). Mutations use Server Actions, then `revalidatePath`. Client-side fetching only where interactivity demands it.
- **API types come only from the generated `schema.d.ts`**; run `make api-sync` after backend changes. Never hand-write API response types.
- Filter state lives in the URL (nuqs).
- Money: always format via `lib/money.ts` (minor units + currency); never divide amounts with floats for display totals.
- UI follows `docs/design/DESIGN.md`; use the existing shadcn components before creating new ones; run the Impeccable audit before finishing a screen.
- Accessibility: labels on every input, keyboard-reachable actions, visible focus.
- Tests: Vitest + RTL for components and utils; MSW handlers typed from the generated types; Playwright for flows.

### 3.4 `AGENTS.md`

One line pointing other tools (Copilot, Cursor, Codex) to `CLAUDE.md` and the docs, so every AI tool gets the same rules:

```markdown
# Agent instructions
This project's AI rules live in [CLAUDE.md](CLAUDE.md) (plus backend/ and frontend/ CLAUDE.md and .claude/rules/). Follow them.
```

---

## 4. Path-scoped rules (`.claude/rules/`)

Rules load only when Claude works on matching files, which keeps root memory lean. Each rule file has a `paths` frontmatter.

| File | Paths | Content outline |
|---|---|---|
| `money.md` | `backend/src/**/domain/**`, `backend/src/**/modules/salaries/**`, `backend/src/**/modules/insights/**`, `frontend/src/lib/money*` | Integer minor units; per-currency exponent (JPY 0, USD 2); reject excess decimals instead of rounding; never sum different currencies; convert to USD only at read time with a dated rate; `Decimal` for rates; display rounding mode; monthly = annual ÷ 12 for display only |
| `testing.md` | `backend/tests/**`, `frontend/**/*.test.ts*`, `frontend/e2e/**` | One behaviour per test; descriptive names (`test_<who>_<does>_<outcome>`); arrange-act-assert; factories over fixtures with hidden data; freeze time; no network or sleeps; every endpoint in the authz matrix; parametrize tables |
| `security.md` | `backend/src/**/core/**`, `backend/src/**/modules/auth/**`, `backend/src/**/modules/ask/**`, `backend/src/**/modules/imports/**`, `backend/src/**/modules/exports/**` | Permissions not roles; masking + small-group rule in services; cookie flags (HttpOnly, Secure, SameSite=Lax); identical error for unknown user and wrong password; CSV formula neutralisation; XLSX values only; upload caps; LLM tool results are data, tools are read-only; never log secrets or full salary rows |
| `api-contract.md` | `backend/src/**/modules/*/router.py`, `backend/src/**/modules/*/schemas.py`, `frontend/src/lib/api/**` | Versioned `/api/v1`; problem+json errors; pagination/sort/filter conventions; `extra="forbid"`; response models declared on every route; run `make api-sync` after changes; the contract job must pass |
| `design.md` | `frontend/src/**` | Mirrors `docs/design/DESIGN.md` (a short hand-written file in v1, if time allows; created during the frontend block): tokens, typography (tabular numerals), spacing scale, component rules, currency labelling, light/dark, a list of anti-patterns to avoid |

---

## 5. Project skills (`.claude/skills/`)

Each skill is a `SKILL.md` with a trigger-style `description` (so Claude invokes it at the right moment) and a numbered procedure. The user can also run it explicitly as `/name`.

### 5.1 `/tdd <behaviour>`
**Trigger:** implementing any behaviour, feature or bug fix in backend or frontend code.
1. Restate the behaviour as one acceptance criterion and pick the lowest test layer that can prove it ([14-testing-strategy.md](14-testing-strategy.md#3-test-pyramid)).
2. Write **one** failing test with a descriptive name. Nothing else.
3. Run only that test and **show that it fails for the expected reason**. If it fails for another reason (import error, fixture bug), fix the test first.
4. Suggest the commit `test(<scope>): <behaviour>`.
5. Write the minimum production code to pass. Run the test, then the module's suite.
6. Suggest the commit `feat(<scope>): …` (or `fix:`).
7. Refactor on green (names, duplication, extraction); re-run; suggest `refactor:` if anything changed.
8. Stop and present the next behaviour candidate. Never batch several behaviours into one cycle.

### 5.2 `/adr <title>`
**Trigger:** a decision is made or changed that affects architecture, data, security, tooling or a trade-off.
1. Find the highest number in `docs/adr/`; the next one is that + 1, zero-padded to 4 digits.
2. Copy `docs/adr/0000-template.md` to `NNNN-<kebab-title>.md`.
3. Fill in Context (the forces), Decision (one paragraph, active voice), Alternatives considered (each with why rejected), Consequences (positive, negative, follow-ups). Status: Proposed.
4. If it supersedes an ADR, mark the old one `Superseded by NNNN` and link both ways.
5. Add it to the ADR index in `docs/README.md`.
6. Ask the user to accept; then set Status: Accepted.

### 5.3 `/verify`
**Trigger:** before saying work is done, before a commit that claims green, before opening a PR.
1. Run `make verify`.
2. If something fails, group the failures by tool (ruff, pyright, pytest, eslint, tsc, vitest, knip, api drift).
3. Report a short table: tool → pass/fail → first relevant error lines.
4. Never report "done" with a failing check. Never skip or disable a check to get green.

### 5.4 `/api-sync`
**Trigger:** any change to a FastAPI router or schema.
1. Run `make api-sync` (export `openapi.json` → regenerate `frontend/src/lib/api/schema.d.ts` → `tsc --noEmit`).
2. If `tsc` fails, list the frontend call sites affected by the contract change and fix them (or reconsider the API change).
3. Make sure MSW handlers still typecheck.
4. Suggest the commit `build(api): regenerate client` (or include it in the feature commit).

### 5.5 `/log-prompt`
**Trigger:** after a material AI interaction: a design decision, generated module, rejected suggestion, AI mistake caught, or research finding.
1. Append an entry to `docs/ai/prompt-log.md` using its template:
   - Date, milestone, intent
   - **Prompt**: the user's real prompt, lightly cleaned for grammar and readability; never invented
   - What the AI produced (a summary)
   - What was **accepted / changed / rejected**, and why
   - Verification performed (tests, docs checked, manual check)
2. Mark the entry `curated` (cleaned) or `verbatim`.
3. Link the related commit or PR when available.

### 5.6 `/new-module <name>`
**Trigger:** adding a new backend feature slice.
1. Read an existing module (e.g. `modules/employees/`) to mirror its conventions. Don't invent a new pattern.
2. Create `modules/<name>/{__init__,router,schemas,service,repository,models}.py` with minimal typed skeletons.
3. Create `tests/unit/test_<name>_*.py` and `tests/integration/test_<name>_api.py` with one placeholder **failing** test describing the first behaviour.
4. Register the router in the app factory; add an entry to the authz matrix (it fails until permissions are declared).
5. If there are models, create an Alembic revision stub.
6. Hand over to `/tdd` for the first behaviour.

### 5.7 `/commit`
**Trigger:** the user asks to commit, or a TDD step is complete.
1. `git status` + `git diff --staged`; if nothing is staged, propose a **single logical** change set to stage.
2. Keep red and green separate: never mix a new failing test and its implementation into one commit when doing TDD pairing.
3. Write a Conventional Commit message (`type(scope): subject` ≤ 72 chars, body for the why).
4. Add the attribution trailer lines the current session provides (default `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`); never hard-code a session link.
5. Commit. Never `--no-verify`, never amend a pushed commit, never push unless asked.

---

## 6. Reviewer subagent (`.claude/agents/reviewer.md`)

- **Role:** read-only code reviewer giving an independent second opinion on a diff.
- **Tools:** Read, Grep, Glob, and Bash limited to `git diff` / `git log` / `git show`. **No Edit or Write.**
- **Input:** a branch or diff range (default `main...HEAD`).
- **Checklist** (derived from CLAUDE.md and the rules):
  1. Was a test added before or with each behaviour (check commit order)? Are the tests meaningful, not just coverage padding?
  2. Money: any float, any cross-currency sum, missing currency on an amount?
  3. Layering: business logic in routers, repositories or Next.js?
  4. Authz: does each new endpoint declare a permission and appear in the matrix? Is masking and the small-group rule applied in the service, not the router or UI?
  5. Audit event for every mutation, in the same transaction?
  6. Input validation (`extra="forbid"`, enums, caps) and problem+json errors?
  7. Security: injection (SQL, CSV formula, prompt), secrets in code or logs, cookie flags.
  8. Contract: client regenerated? Breaking API changes called out?
  9. Readability: naming, function size, dead code.
- **Output:** one line per finding, `path:line — severity — problem — suggested fix`, most severe first. No praise, no style nits that formatters already handle.
- **Use:** before opening each milestone PR. Findings and resolutions are summarized in the PR's "AI usage" section.

The built-in `/code-review` and `/security-review` commands are also run before submission (section 9).

---

## 7. `settings.json`: permissions and hooks

### 7.1 Permissions

As committed in `.claude/settings.json`:

```jsonc
{
  "permissions": {
    "allow": [
      "Bash(make:*)", "Bash(uv:*)", "Bash(uvx:*)", "Bash(pnpm:*)", "Bash(npx:*)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git checkout:*)", "Bash(git switch:*)",
      "Bash(git branch:*)", "Bash(git merge:*)", "Bash(git worktree:*)", "Bash(git push:*)",
      "Read(./**)", "Edit(./**)", "Write(./**)"
    ],
    "deny": [
      "Read(./**/.env)", "Read(./**/.env.local)", "Read(./**/.env.development)",
      "Read(./**/.env.production)", "Read(./**/.env.test)",
      "Edit(./**/.env)", "Edit(./**/.env.local)", "Edit(./**/.env.development)",
      "Edit(./**/.env.production)", "Edit(./**/.env.test)",
      "Bash(git push --force:*)", "Bash(git push -f:*)", "Bash(git push --force-with-lease:*)",
      "Bash(git checkout -- :*)", "Bash(git checkout .:*)", "Bash(git branch -D:*)",
      "Bash(git reset --hard:*)", "Bash(git clean:*)", "Bash(git worktree remove --force:*)",
      "Bash(rm -rf:*)",
      "Bash(curl:*)", "Bash(wget:*)"
    ],
    "ask": [
      "Bash(turso:*)", "Bash(vercel:*)"
    ]
  }
}
```

- **Allow:** routine, reversible, local operations so TDD loops run without prompts. Plain `git push` is allowed because the build is run by an autonomous orchestrator that pushes after each block.
- **Deny:** reading or editing secrets, force pushes, git commands that discard work (checkout `--`/`.`, `branch -D`, `reset --hard`, `clean`, `worktree remove --force`), destructive commands, raw network fetches from the shell (research goes through the web tools, where it's visible). Deny wins over allow.
- **Ask:** deploy and database cloud CLIs (`vercel`, `turso`).
- `.env.example` remains readable and editable (it holds no secrets): the deny patterns name `.env` and `.env.<env>` files explicitly instead of `.env.*`. The PreToolUse hooks (§7.2) cover every other `.env.<name>` (e.g. `.env.development.local`) for Read, Edit and Write, and in Bash commands.
- Allow rules match a command prefix only, so `Bash(uv:*)`, `Bash(npx:*)` and `Bash(pnpm:*)` would let `uv run cat .env`, `npx vercel` or `git push origin main --force` through. `guard-bash.sh` closes that gap.

### 7.2 Hooks

| Event | Matcher | Script | Behaviour |
|---|---|---|---|
| **PreToolUse** | `Read\|Edit\|MultiEdit\|Write` | `.claude/hooks/block-protected-files.sh` | Read: blocks any `.env` / `.env.<name>` file except `.env.example` ("secrets files are not readable by agents"). Edit/Write: also blocks `uv.lock`, `pnpm-lock.yaml`, `frontend/src/lib/api/schema.d.ts` and `frontend/openapi.json` (generated), with a message naming the command to use instead (`uv add`, `pnpm add`, `make api-sync`). Paths match by name or suffix, after resolving `..`, so git worktrees are covered |
| **PreToolUse** | `Bash` | `.claude/hooks/guard-bash.sh` | Parses the command (python3 `shlex`; quoted text and heredoc bodies are arguments) and finds command words, also through `env`, `sudo`, `uv run`, `uvx`, `npx`, `pnpm exec`/`dlx` and `bash -c`. Blocks a `.env` / `.env.<name>` reference other than `.env.example`, `curl`/`wget`, and `git push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes`, `--mirror`, `--delete`, `-d`, `--prune`, `+refspec` or `:ref`. Returns `permissionDecision: "ask"` for `vercel`/`turso` |
| **PostToolUse** | `Edit\|MultiEdit\|Write` | `.claude/hooks/format-changed-file.sh` | For `*.py` under `backend/`: `uv run ruff format <file>` and `uv run ruff check --fix --ignore F401 <file>` (an import added in one edit is used in the next; lefthook and CI still catch unused imports). For `*.ts, *.tsx, *.css, *.json, *.md` under `frontend/`: `pnpm prettier --write <file>`. The project root is the nearest folder above the file with `backend/pyproject.toml` or `frontend/package.json`, so a worktree uses its own tools. Non-blocking; a no-op until the tool is installed; failures are reported back to Claude (exit 2) |

`.claude/hooks/test-hooks.sh` pipes sample hook JSON into each hook and checks the results (PASS/FAIL, non-zero exit on any failure). Run it after changing a hook.

Why hooks instead of instructions: formatting and protected files are "every time, no exceptions" rules, and Anthropic's guidance is to move such rules from CLAUDE.md into hooks, which are deterministic.

---

## 8. MCP servers (`.mcp.json`)

| Server | Purpose | Why |
|---|---|---|
| **Context7** | Fetches current, version-specific library documentation into context (Next.js 16, FastAPI, SQLAlchemy 2.x, Tailwind v4, shadcn, TanStack, nuqs) | The model's training data may predate recent APIs. Next 16 removed `next lint` and renamed middleware to `proxy.ts`. Current docs prevent stale code |
| **Playwright MCP** | Lets Claude drive a real browser against `make dev`: navigate, click, screenshot, read the console | Claude can check its own UI work (layout, flows, errors) before claiming done. Complements the Playwright test suite |

Both are development-time only; neither is used by the running application. The user's Chrome extension may also be used ad hoc, but the committed project config uses Playwright MCP so it works in any environment.

---

## 9. Existing skills and commands used

| Skill / command | When | Notes |
|---|---|---|
| **frontend-design** (official Anthropic skill) | While building each screen | Guidance on typography, layout and avoiding a templated look |
| **Impeccable** (`pbakaus/impeccable`, Apache 2.0) | Audit of each screen before its frontend PR merges | Anti-"AI slop" rules (gradients, Inter-everywhere, nested cards, cramped spacing). **Its files are reviewed before install**, because third-party skills can ship scripts and hooks. Audit findings go in the prompt log |
| **Claude Design / `/design`** | **Cut from v1** (future work) | Canvases with 2 options for each of 5 key screens → the user picks → frozen into `docs/design/DESIGN.md` ([adr/0018-design-workflow.md](adr/0018-design-workflow.md)) |
| **`/code-review`** | Before each milestone PR and before submission | Correctness-focused review of the diff |
| **`/security-review`** | Before submission, and after the auth, import and ask milestones | Security pass over pending changes |

---

## 10. Prompt-log policy

- **Real prompts only.** Entries contain what the user actually asked, in their own words, lightly cleaned for grammar and readability and labelled **curated**. Nothing is invented or rewritten to look more sophisticated. Interviewers will probe the AI workflow live, and the log must match what really happened.
- **Record the corrections.** The most valuable entries show where the AI was wrong, outdated or over-scoped and how that was caught. Examples from planning: Auth.js turned out to be in maintenance mode; Fly.io and Railway have no free tier; Render's free tier has no persistent disk for SQLite; Gemini's free tier may train on prompts.
- **Record the verification.** Each entry notes how the output was checked (tests, docs, a manual run).
- **Granularity.** One entry per material interaction, not per keystroke. Routine completions aren't logged.
- The planning session that produced these docs is the log's first set of entries ([ai/prompt-log.md](ai/prompt-log.md)).
