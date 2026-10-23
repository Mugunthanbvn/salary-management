# AI-Assisted Development Workflow

This document describes **how AI is used** to build the ACME Salary Management system, and how its output is kept correct. Incubyte's stated stance is that "AI compounds whatever a team already brings": spec before code, tests that define "done", and AI output reviewed like a colleague's work. This workflow follows that.

- **Primary tool:** Claude Code (CLI + VS Code extension), model Claude Opus 5.5, used as a pair programmer.
- **Human role:** the candidate makes every product and architecture decision. AI researches, proposes options with trade-offs, drafts, implements under TDD, and reviews.
- **Traceability:** every significant decision is an ADR in [../adr/](../adr/), and key prompts are recorded in [prompt-log.md](prompt-log.md).

---

## 1. Principles

1. **Decisions are human; options are AI.** AI must present alternatives with pros and cons and a recommendation. The candidate chooses. Example: the hosting decision went through four rounds ([ADR-0016](../adr/0016-deploy-vercel-turso.md)).
2. **Spec before code.** Requirements, PRD and ADRs exist before the first line of application code ([../02-requirements-one-pager.md](../02-requirements-one-pager.md) is commit #1).
3. **Tests define done.** No production code without a failing test first ([../14-testing-strategy.md](../14-testing-strategy.md)).
4. **Verify, don't trust.** Every factual claim the AI makes about versions, free tiers or library status is checked against a source, and conflicting sources are called out (see §7).
5. **Honest logs.** The prompt log contains real prompts (lightly cleaned), including places where the AI was wrong or overreached.

---

## 2. Phase by phase

### 2.1 Research
- **What AI does:** reads the brief (the `.docx`), researches Incubyte's engineering culture (website, hiring blog), scans about 9 public candidate submissions of the same assessment for common gaps, and researches technology options (currency storage standards, free hosting tiers, auth library status, LLM free tiers, tooling).
- **How it's verified:**
  - Each finding cites its source.
  - Third-party and aggregator data is flagged as such; conflicting numbers are reported as conflicts, not averaged.
  - Unverifiable claims are marked "verify at signup / at scaffold".
- **Output:** [../04-research.md](../04-research.md).

### 2.2 Brainstorming and planning (Claude Code *plan mode*)
- Plan mode is read-only: the AI can research and ask questions but cannot change files (except the plan file).
- Decisions are made through structured multiple-choice questions, each with a recommended option and a trade-off description.
- The candidate repeatedly declined to leave plan mode until every area had been discussed (DB, currency, auth, hosting, scope, data model, AI feature, tooling, design). This is deliberate: "brainstorm with me throughout development so I'm aware of all decisions".
- **Output:** a single plan file → these docs.

### 2.3 Specification and docs
- AI drafts the PRD, requirements one-pager, architecture, data model, API spec, ADRs, etc. **from the approved plan only**: no new decisions; unknowns marked **TBD**.
- **Parallel forked agents** were used to write the docs folder. Each fork inherits the full planning conversation and writes a disjoint set of files, so the documents stay consistent while being written in parallel. The main session then cross-checks links, numbering and consistency.
- The candidate reviews all docs in a fresh session before any build starts.

### 2.4 Implementation: the TDD loop
Per behaviour, via the project skill `/tdd <behaviour>` ([../16-claude-code-setup.md](../16-claude-code-setup.md)):

1. **Red.** Write the smallest failing test that expresses the behaviour. Run it and confirm it fails *for the right reason*.
2. **Green.** Write the minimal code to pass.
3. **Refactor.** Improve names and structure with tests green.
4. **Commit.** `test:` (red) and `feat:` (green) as separate Conventional Commits where it aids readability (`/commit`), plus `refactor:` when applicable.

Additional rules (enforced by `CLAUDE.md`, `.claude/rules/*.md`, hooks):
- Money is never a float ([ADR-0004](../adr/0004-money-integer-minor-units.md)).
- Layering is router → service → repository.
- Permissions are checked by permission, never by role name.
- No business logic in Next.js.
- Generated files (API client, lockfiles) are never hand-edited (a PreToolUse hook blocks it).
- **Context7 MCP** supplies current library docs, so the AI doesn't write outdated Next.js 16 / FastAPI APIs from older training data.

### 2.5 Review
- **Reviewer subagent** (`.claude/agents/reviewer.md`): read-only. Reviews each diff against the project rules (TDD evidence, money handling, layering, authz, audit events, tests for each behaviour).
- **`/code-review`** for correctness and **`/security-review`** before submission.
- **CI** is the final gate: ruff, pyright, pytest (SQLite + Postgres job), eslint, tsc, vitest, knip, contract drift, Playwright, pip-audit, pnpm audit, gitleaks, CodeQL ([../15-tooling-devex.md](../15-tooling-devex.md)).
- The candidate reads every PR before merging (one PR per milestone, merge commits so the incremental history is preserved).

### 2.6 Design
- **Claude Design / `/design`:** 2 options for each of the 5 key screens; the candidate picks. The result is frozen as `docs/design/DESIGN.md` and mirrored to `.claude/rules/design.md` ([ADR-0018](../adr/0018-design-workflow.md)).
- **frontend-design** (official skill) guides implementation.
- **Impeccable** (anti-"AI slop" skill, reviewed before install) audits each screen before its PR merges. Findings and fixes are logged in the prompt log.
- **Playwright MCP** lets the AI open the running app and check its own UI work.

### 2.7 AI inside the product
The "Ask about pay" feature is designed with the same discipline: read-only tools, permission-scoped, deterministic tests with a fake LLM, plus a committed evaluation set and model comparison ([../10-ai-ask-design.md](../10-ai-ask-design.md), [evals/README.md](evals/README.md)).

---

## 3. What the AI is NOT allowed to do

Enforced by `.claude/settings.json` (permissions + hooks), not just by instructions:

| Forbidden | Mechanism |
|---|---|
| Read `.env*` files / secrets | `permissions.deny` |
| `git push --force`, `rm -rf` | `permissions.deny` |
| Hand-edit `uv.lock`, `pnpm-lock.yaml`, the generated API client | PreToolUse hook blocks the edit |
| Commit or push without the candidate asking | Claude Code default behaviour + CLAUDE.md rule |
| Make product or architecture decisions alone | Working agreement: options + recommendation, the candidate decides |
| Install third-party skills/plugins without review | Working agreement (Impeccable is reviewed first) |

Allowed without prompting: `make *`, `uv run *`, `pnpm *`, read-only git commands.

---

## 4. Verification habits

- **Sources over memory.** Library status (e.g. Auth.js in maintenance mode, SQLAlchemy 2.1 at rc2, `next lint` removed in Next 16, ty in beta) was checked online, not assumed.
- **Flag uncertainty.** Free-tier limits that differ between sources are recorded as ranges and marked "verify".
- **Spike risky assumptions early.** The Turso driver, Vercel rewrite and Safari cookie behaviour are validated in milestone 1 before building on them.
- **Prove portability claims.** The "swap DB by URL" claim is proven by a Postgres CI job, not asserted.
- **Tests and evals define done.** Unit and integration tests for code, the eval set for AI answers.
- **Read before running.** Downloaded third-party content (skills, scripts) is read before execution.

---

## 5. Artifacts produced by this workflow

| Artifact | Location |
|---|---|
| Curated prompt log | [prompt-log.md](prompt-log.md) |
| Architecture Decision Records | [../adr/](../adr/) |
| Research notes with sources | [../04-research.md](../04-research.md) |
| Claude Code configuration (CLAUDE.md, rules, skills, agents, hooks) | repo root + `.claude/`, described in [../16-claude-code-setup.md](../16-claude-code-setup.md) |
| Ask eval set + model comparison | [evals/](evals/) (milestone 13) |
| PR descriptions with an "AI usage" section | GitHub PRs (template in `.github/`) |
