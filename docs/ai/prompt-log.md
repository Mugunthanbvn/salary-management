# Prompt Log: Planning Session (2026-10-23 → 2026-10-24)

> **Curated: prompts lightly edited for readability; meaning unchanged.**
> These are the candidate's real prompts from the Claude Code planning session (plan mode), in chronological order. Answers to multiple-choice questions are included where they changed the direction. "AI proposed" summarises Claude's response; "Decision" is what the candidate chose. Entries where the AI was corrected or overreached are marked **⚠ correction**.

Tool: Claude Code (VS Code extension), model Claude Opus 5.5, plan mode (read-only until approval).

---

### 1. Kick-off: understand the assessment and the company
- **Intent:** start the project the right way; align with what Incubyte expects.
- **Prompt:** *(pasted Incubyte's invitation email + the assessment .docx)* "We have to implement this in the best way possible. Brainstorm with me throughout development so I'm aware of all development decisions. The boilerplate should be set up to industry standard; check the company URLs, their standards and their projects, and what they will expect. Use all the latest versions. Use Next.js for the UI and FastAPI for the backend. Brainstorm."
- **AI proposed:**
  - Extracted the brief.
  - Researched Incubyte's hiring blog and website: TDD is mandatory, spec before code, "AI compounds what a team brings", and their open-source Claude Code plugin "Bee".
  - Surfaced hidden product traps: multi-country means multiple currencies; "managed in Excel" means import/export matters; "answer questions about pay" means insights; "ask, don't assume" means a clarification email.
  - Asked four decision questions (DB, currency, AI feature, deployment).
- **Decision:** see entries 2–3.
- **Why it matters:** set the evaluation lens (TDD, spec-first, judgment over complexity) before any technical choice.

### 2. Database: keep it swappable
- **Intent:** avoid locking into a DB early.
- **Prompt:** "Can we use an ORM for now, so we can easily switch to SQLite later by changing only the connection string? Deployment should be free."
- **AI proposed:** SQLAlchemy 2.x ORM + Alembic, configured only by `DATABASE_URL`. Initially SQLite for dev/tests and Neon Postgres in prod, with CI on both databases.
- **Decision:** ORM accepted. The prod DB was revisited later (entries 9–11).
- **Why it matters:** the "swap by URL" requirement became a testable claim (a Postgres CI job).

### 3. Currency: research the standard
- **Intent:** don't guess how to store multi-currency money.
- **Prompt:** "What's the standard solution for multi-country currency storage and calculation? Check online."
- **AI proposed:**
  - Integer minor units + ISO 4217 code, with per-currency exponents (JPY = 0).
  - Convert at read time only and never persist converted values; show the FX rate date.
  - Noted that SQLite has no true DECIMAL, so integers are the only portable choice.
- **Decision:** accepted ([ADR-0004](../adr/0004-money-integer-minor-units.md), [ADR-0005](../adr/0005-fx-read-time-conversion.md)).
- **Why it matters:** turned a research question into a defensible, sourced decision.

### 4. Scope, auth, competitor research, AI artifacts
- **Intent:** set the feature scope and learn from others who took the same assessment.
- **Prompts (answers to the scope round):**
  - Auth: "Full auth (Auth.js + roles)."
  - Extra features: "CSV export, salary change history, and what does the pay-equity view mean?"
  - Clarification email: "Check online for any public GitHub repos to gather insights about this company, existing products and candidate assessments."
  - AI workflow artifacts: "CLAUDE.md + ADRs, and a prompt log (rephrased to show prompting skills)."
- **AI proposed:**
  - A competitor scan of about 9 public submissions. Common gaps: single shared login, no AI feature, percentiles tested only on Postgres, weak FX handling, often not deployed.
  - Explained compa-ratio pay equity.
  - Flagged that **Auth.js is in maintenance mode** (Better Auth took over in Sept 2025).
  - On the prompt log: recommended keeping *real* prompts, lightly cleaned and labelled "curated", rather than rewritten ones, because interviewers will probe the AI workflow live.
- **Decision:** competitor gaps became our differentiators; the prompt-log policy was adopted (this file).
- **Why it matters:** scope driven by evidence; honesty policy for AI artifacts.

### 5. Auth: question the architecture
- **Intent:** understand before accepting a proposal.
- **Prompts:**
  - "Why do we need a BFF? Explain clearly."
  - Roles: "Admin / HR Manager / Viewer."
  - Pay equity: "I asked you to include it, not just explain what it is."
- **AI proposed:**
  - Explained the cross-site cookie problem (web and API on different sites), httpOnly cookies and SSR.
  - Moved pay equity into the core scope.
- **⚠ correction:** the AI had treated "what does pay-equity mean" as a question only; the candidate wanted the feature included **and** explained.
- **Decision:** 3 roles; pay equity in core.

### 6. Mid-turn request: Claude tooling
- **Prompt:** "Add the required Claude skills and commands for this project."
- **AI proposed:** project skills `/tdd`, `/adr`, `/verify`, `/api-sync`, `/log-prompt`, `/new-module`; a reviewer subagent; a formatting hook; settings permissions.
- **Decision:** accepted; later extended with `/commit`, rules files, MCP servers ([../16-claude-code-setup.md](../16-claude-code-setup.md)).

### 7. Auth alternatives
- **Intent:** see the full option space before deciding.
- **Prompt:** "Just brainstorm more with me. Without a BFF, what are the other methods?"
- **AI proposed:** six alternatives compared on XSS safety, SSR, cost, Safari compatibility and complexity:
  - Bearer token in localStorage;
  - cross-site cookie;
  - shared custom domain;
  - FastAPI serving a static export;
  - FastAPI on Vercel as well;
  - hosted auth provider.
  Clarified that the "BFF" is really just a Next `rewrites` rule.
- **Decision:** FastAPI-owned auth + same-origin rewrite ([ADR-0008](../adr/0008-fastapi-auth-same-origin-rewrite.md)).

### 8. SQLite and competitors
- **Prompt:** "Which hosting supports SQLite? Which DB do our competitors use? Since it's 10K records, we can use SQLite, right?"
- **AI proposed:**
  - Competitor DBs: the strongest used SQLite; others used Postgres.
  - Confirmed SQLite is sufficient at this scale.
  - Explained that hosting, not SQLite, is the constraint (it needs a persistent disk).
- **⚠ overreach:** the AI looked at the candidate's unrelated `oci` workspace, found an Oracle Cloud VM with Coolify, and recommended self-hosting on it.

### 9. Redirect: popular free hosting, not own infrastructure
- **Prompt:** "No Coolify, not our own instances. Use the free options that are popular for this stack."
- **AI proposed:** verified that Vercel now runs FastAPI with zero config, and proposed Vercel (web) + Vercel (API) + Neon Postgres with a single rewrite rule.
- **Decision:** own infrastructure rejected ([ADR-0016](../adr/0016-deploy-vercel-turso.md)).
- **Why it matters:** the candidate kept the solution conventional and reviewer-friendly.

### 10. Push back: SQLite in production
- **Prompt:** "No, we can use SQLite instead of Postgres for 10k records. What do you think?"
- **AI proposed:**
  - Agreed. Proposed **Turso** (hosted SQLite/libSQL, free, no sleeping), so one dialect everywhere.
  - Flagged the Turso Python driver as young (the original repo was archived June 2025).
  - Mitigation: a day-1 deploy spike and Neon as a URL-only fallback.
- **Decision:** SQLite everywhere + Turso ([ADR-0002](../adr/0002-sqlite-everywhere-turso.md)).

### 11. Fly.io / Railway?
- **Prompt:** "What happened to Fly/Railway for Python?"
- **AI proposed:** both support plain SQLite on volumes but have **no free tier** (Fly: 7-day trial; Railway: 30-day trial then $5/mo). Trial expiry could kill the demo mid-review.
- **Decision:** "Vercel + Turso, $0."

### 12. Scope audit against a feature checklist
- **Intent:** make sure nothing important is missing.
- **Prompt:** *(pasted a detailed feature list: profiles, salary structure, import/export, search/filters/reports, access control, audit, encryption, backups, usability)* "Among these, what is left and what have we already considered?"
- **AI proposed:** a three-way mapping (covered / partial / not covered) with effort estimates, plus a reminder that the brief values judgment over complexity.
- **Decision:** see entry 13.

### 13. Explain compensation and roles in simple terms
- **Prompts:**
  - "Explain this part [compensation components] in simple terms."
  - "What roles have we planned, and what's good to have?"
  - "XLSX export, audit log, filters + report gaps, hiding confidential salaries by role. We can have bulk import/export; since the initial data is in Excel, import will be very helpful. What are bonuses, allowances and salary components? Explain."
- **AI proposed:**
  - A worked example (base + HRA + transport + target bonus = total comp) and why base-only comparisons mislead.
  - A role/permission matrix.
  - A **small-group rule** (hide aggregates over fewer than 3 people for Viewers).
- **Decision:**
  - Base + components table ([ADR-0010](../adr/0010-compensation-components.md)).
  - 3 roles with permission matrix + small-group rule ([ADR-0009](../adr/0009-permission-rbac-small-group-rule.md)).
  - Audit log ([ADR-0011](../adr/0011-audit-events.md)) and XLSX export.

### 14. Import formats: changed mind
- **Prompts:** first "CSV only", then (interrupting) "We can have CSV + Excel."
- **Decision:** one pipeline for CSV + XLSX with dry-run and all-or-nothing commit ([ADR-0012](../adr/0012-bulk-import-dry-run.md)).
- **Why it matters:** the candidate re-applied the product insight ("the data lives in Excel") to the import decision.

### 15. Data model and seed
- **Prompt:** chose "Data model / seed details" as the next topic.
- **AI proposed:**
  - Employee fields with data minimisation (no DOB, gender, address, bank details).
  - A controlled job-title list (free text would fragment pay-equity cohorts).
  - Employment type, with insights defaulting to full-time.
  - 10 countries covering edge cases (EUR shared by two countries, zero-decimal JPY).
  - A seed formula and a documented "demo story".
- **Decision:** all recommendations accepted.

### 16. AI feature: explain first
- **Prompt:** "First explain what the AI feature is, then ask the questions, lol."
- **⚠ correction:** the AI had jumped straight into a tool table, guardrails and model choice before describing the feature from the user's point of view. It re-explained it with a concrete HR conversation ("Are we underpaying anyone in Germany?" → answer with figures, FX date, "How I got this", follow-up "And in India?").
- **Lesson recorded:** explain the *what* and *why* in plain language before the *how*.

### 17. Free LLM provider
- **Prompts:**
  - Model: "A Gemini personal key or a Groq free API key."
  - Follow-ups: "Yes, follow-ups work."
  - Waiting UX: "Just a spinner."
  - Quality: "Test question set."
  - Then provider order: "Gemini default, Groq alternative."
- **AI proposed:**
  - Researched both free tiers.
  - One OpenAI-compatible adapter for both providers.
  - Flagged that **Gemini's free tier may train on prompts**: fine for synthetic demo data, not for real HR data.
  - Flagged Groq's tokens-per-minute limit.
- **Decision:** [ADR-0015](../adr/0015-ai-ask-tool-calling.md); eval set ([evals/README.md](evals/README.md)).

### 18. Tooling R&D
- **Prompts:**
  - "Do R&D on the latest tools, packages, code quality tools, dev tools, Makefile, uv, GitHub tools, Claude setup and CLAUDE.md files necessary for this project, and add them to the plan."
  - Then: "Explain all these tools to me now."
- **AI proposed:**
  - Researched type checkers (Pyright vs mypy / ty / Pyrefly), Biome vs ESLint (Next 16 removed `next lint`), git hook managers, dependency bots, OpenAPI client generators, SQLAlchemy 2.1 status, and Claude Code practices (CLAUDE.md under 200 lines, path-scoped rules, hooks, skills).
  - Then a plain-language explanation of every tool.
- **Decision:** "All as recommended" ([ADR-0017](../adr/0017-toolchain.md)). Git flow: one PR per milestone with merge commits. MCP: Context7 + Playwright.

### 19. Design tooling
- **Prompt:** "For design, use skills like the official Claude frontend one, and also an AI-slop design skill. For generating screen designs, should we use the Google Stitch CLI or Claude's /design command?"
- **AI proposed:** compared Stitch, Claude Design, frontend-design and Impeccable (anti-slop). Recommended Claude Design → DESIGN.md → frontend-design → Impeccable audit, with Impeccable's files reviewed before install.
- **Decision:** accepted ([ADR-0018](../adr/0018-design-workflow.md)).

### 20. Plan approval and docs
- **Context:** the candidate rejected the plan-approval step several times in order to keep brainstorming.
- **Prompt:** "Create a docs folder that has every document; I will review it in a new session. Make the docs as detailed as possible: not a single doc, but different docs like the PRD, plan…"
- **AI proposed:** the docs structure (PRD, one-pager, clarifications, research, architecture, data model, API spec, security, insights, AI design, import/export, seed, UX, testing, tooling, Claude setup, deployment, implementation plan, performance, trade-offs, 18 ADRs, AI workflow, this log). Written by parallel forked agents sharing the same planning context, then cross-checked.
- **Decision:** approved, scoped to docs only (no code, no `git init`).

### 21. Doc cross-check finds a design flaw; decisions delegated
- **Context:** while writing [09-insights-pay-equity.md](../09-insights-pay-equity.md), one of the forked doc writers found that the agreed pay-equity design (**compa-ratio = salary ÷ peer-cohort median**) can't detect the planted demo story. If the whole Customer Success team in Germany is paid 8% less, the cohort median drops 8% too, and nobody is flagged. **⚠ correction (AI self-correction):** the flaw was in a design the AI had proposed earlier.
- **AI surfaced:** the flaw plus six other open points (small-group threshold 3 vs 5, import create-only vs upsert, session policy, retention/erasure, Singapore names in the seed), with options for each.
- **Prompt:** "You decide all."
- **AI decided:**
  - **Pay bands:** add `pay_bands` (role × level × country); compa-ratio = base ÷ band midpoint (the standard HR definition); add a department rollup that flags teams with a median compa-ratio below 0.95.
  - **Small groups:** n < 5 hidden for Viewers.
  - **Import:** create-only.
  - **Sessions:** 8 h JWT + lockout.
  - **Retention / erasure:** out of scope.
  - **Seed:** curated Singapore name lists.

  All applied across the affected docs; recorded in [README](../README.md) "Decisions made".
- **Why it matters:** the cross-check caught a correctness bug *before code*, which is cheap. It also shows that the tests for the demo story ([14-testing-strategy.md](../14-testing-strategy.md)) would have failed against the original design.

### 22. Hostile design review, then a 1–2 day scope cut
- **Context:** a fresh session, before any code.
- **Prompt:** *(pasted)* "You are a principal engineer and a hostile design reviewer. Your job is to ATTACK the design in this repo and decide whether it is ready for implementation…" (full prompt: requirement coverage, internal consistency, domain correctness, security, platform feasibility, scope vs time, testability, data model, AI feature, unverified assumptions; every finding with a failure scenario, severity and confidence).
- **AI produced:** verdict **READY WITH FIXES**. Three blockers: scope far too large for a fast submission; milestone order broke dependencies (employees needed salary records from a later milestone; login lockout needed the audit table from a later milestone); conflicting names across docs (audit actions in three spellings, small-group threshold 3 vs 5). Majors included Viewer privacy leaks (min/max, totals minus visible groups, `compare_groups`), compa-ratio dividing a USD salary by a EUR band, part-timers all flagged underpaid, login through a Server Action never setting the browser cookie, and the 1 MB Server Action body limit.
- **Follow-up prompts:** "1 day if possible, if not 2 days max" · "what does preview deployment mean" · "employees across multiple countries: how is salary managed, generally multi-currency?" · "cut: Postgres CI job, Claude Design phase, the whole admin UI, raises insight, histogram, Groq and the model comparison, Dependabot/CodeQL/knip, most Playwright tests, previews, non-local salary currency" · "CSV + XLSX import, export" (keep import).
- **Decision:** v1 scope cut recorded in the [docs README](../README.md#v1-scope-decided-2026-10-24-read-this-first); the implementation plan rewritten as ten build blocks over two days ([18](../18-implementation-plan.md)), with audit moved into the auth block and salary records into the employees block; every salary in its country's currency. CSV + XLSX import kept in full.
- **⚠ correction:** the review showed the earlier plan was about 2–3 weeks of work, which contradicted the brief's "least possible time".
- **Follow-up ("proceed"):** added [glossary.md](../glossary.md) as the single source for names, enums, audit actions, error codes, env vars and numbers, and aligned every doc to it (audit actions now `ask.query` etc.; threshold 5 everywhere; Ask errors 429 / 502 / 503; Ask flag via `/auth/me`; one import response shape; half-even rounding; one env-var set).
- **Still open from the review:** Viewer min/max hiding, `compare_groups` suppression, part-time compa-ratio.

### 23. Screen designs with the Stitch CLI, fully mobile responsive
- **Prompts:** "If I generate design with Stitch or Claude, what instruction do I give for both?" · "Can we provide a single doc to the Stitch CLI and generate the design?" · "Check, recently Google launched Stitch CLI" · "Use the Stitch CLI command to generate designs for this project" · "Screens should be full mobile responsive, update in docs as well" · "Generate a version of the design that's mobile responsive as well".
- **⚠ correction:** the AI first said there was no official Stitch CLI. Asked to check again, it found Google's `@google/stitch` CLI (announced October 2026) and corrected itself.
- **AI produced:** a shared brief, a design-system file and one prompt per screen (since removed from the repo); a Stitch project and design system (Geist, one deep-teal accent, 4 px radius); `generate.sh`, which renders 6 screens for desktop and mobile and downloads HTML + PNG. Rewrote [13-frontend-ux.md](../13-frontend-ux.md) §8 to "fully mobile responsive" (tables become cards, filters in a bottom sheet, full-screen sheets, 44 px touch targets) and updated the PRD, testing strategy, plan and glossary.
- **Decision:** the designs are a reference, not a spec; the docs win on behaviour. The Claude Design phase stays cut.
- **Follow-up prompt:** "Page looks like AI developed it, should be creative, new."
- **⚠ correction:** v1 hit the usual AI-dashboard tells (slate + teal, card grids, KPI tiles, all-caps labels, pill badges). The AI wrote a new art direction, "Bands": pay shown as a position in a range, with a band strip as the one signature element; one Prussian-blue ink plus crimson/ochre signals; Archivo Narrow + Public Sans; no cards, tiles or badges. Regenerated all 12 screens in a new Stitch project (v2) and wrote its rules into a DESIGN.md.
- **Follow-up prompts:** `/design` → "Fresh ACME Pay direction" · "Will keep Claude designs, remove Gemini Stitch designs and commit."
- **AI produced:** a third direction in Claude Design, "Marked-up printout": every section leads with HR's question; key figures get a highlighter mark, problems a red-pen underline or circle, notes sit in the margin; Source Serif 4 + Atkinson Hyperlegible Next; 6 desktop + 3 phone artboards.
- **Decision:** keep the Claude Design canvas ([design/claude](../design/claude/README.md)); delete both Stitch directions from the repo; rewrite [design/DESIGN.md](../design/DESIGN.md) for "Marked-up printout".

---

## Observations

- **The candidate drove the key reversals:** ORM portability (2), researching standards (3), questioning the auth architecture (5, 7), refusing self-hosting (9), choosing SQLite in prod (10), adding Excel import (14), free LLMs (17).
- **AI corrections:** treating a "what is X" question as explanation-only (5); recommending the candidate's personal VM (8); explaining implementation before the feature itself (16); its own pay-equity benchmark design, caught during doc cross-checking (21).
- **AI contributions that changed the plan:**
  - Auth.js maintenance status (4).
  - The Public Suffix List / third-party cookie issue (5, 7).
  - The SQLite DECIMAL limitation (3).
  - The free-tier reality check for hosting (8–11).
  - The small-group privacy rule (13).
  - The Gemini free-tier training caveat (17).
  - "Squash merges would erase the incremental history" (18).

Implementation-phase prompts will be appended below via `/log-prompt`, using the same format.

---

# Build session (2026-10-24): orchestrator + subagents

> **Curated.** One Claude Code session (cloud, auto mode) acted as the lead engineer and orchestrator described in [prompts/build-orchestrator.md](prompts/build-orchestrator.md). It planned the work, gave each build block to a subagent with a self-contained brief, had a fresh reviewer subagent check every block, fixed the findings test-first, and merged each block with a merge commit. Decisions the orchestrator took on its own (the user delegated them) are listed per block below.

### 24. Kick-off: build the whole app with subagents
- **Prompt:** "Read docs/ai/prompts/build-orchestrator.md and follow everything below the divider line exactly. You are the lead engineer and orchestrator described there: build the whole app with subagents, decide any open questions yourself, and leave only deployment pending."
- **Decisions taken by the orchestrator (no user available, precedence rule applied):**
  - **Integration branch.** The cloud session may push only to its designated branch `claude/build-app-subagents-hxxp6x`. That branch plays the role of `main` in the orchestrator prompt: each block branch (`bNN-slug`) is created from it and merged back with `git merge --no-ff`; only the integration branch is pushed. Merging it into `main` is left to the user (a normal PR merge with a merge commit keeps the history).
  - **Runtimes.** Python **3.13** (the orchestrator prompt prefers it; Vercel supports 3.12–3.14; it is the version installed in the build container). Node **22** (installed in the build container; Next.js 16 supports it; Vercel supports it). Docs that said 3.14 / Node 24 are updated.
  - **`git push` allowed** in `.claude/settings.json` (force pushes stay denied, `vercel`/`turso` stay in "ask"), because an autonomous session cannot answer a permission prompt after every block.
  - **Playwright pinned to 1.63.0**, the version whose browsers are pre-installed in the build container.
  - **Ask page built in B9**, together with `POST /ask`, because the page's types are generated from the endpoint's OpenAPI schema.
  - **No LLM key in the build environment**, so `make eval-ask` is not run; the eval set is written and the run is listed as pending.

### 25. B0: Claude Code project setup, and what the independent review caught
- **Brief (orchestrator → subagent):** build the files in [16-claude-code-setup.md](../16-claude-code-setup.md) trimmed to the v1 scope: CLAUDE.md files, rules, skills (`/tdd`, `/commit`, …), the reviewer agent, settings with permissions and hooks, `.mcp.json`.
- **Subagent decisions:** lockfiles are blocked by file name anywhere in the repo; the format hook uses only the project's own ruff/prettier; `design.md` is light theme only (DESIGN.md has no dark palette); Playwright MCP runs headless.
- **⚠ correction (independent reviewer subagent):** the first version had real holes. Broad `Bash(uv:*)`/`pnpm`/`npx` allow rules let `uv run cat backend/.env` or `npx vercel` through; `git push origin main --force` passed because the deny rules only match a prefix; edits to generated files inside a git worktree were not blocked; the `/new-module` skill committed production code under a `test:` commit; the commit trailer hard-coded this session's link for every future session.
- **Fix:** a hook test harness was written first (`.claude/hooks/test-hooks.sh`, 145 checks), then each hole was reproduced by a failing check and fixed: a new `guard-bash.sh` PreToolUse hook (blocks `.env` reads, curl/wget and force/mirror/delete pushes wherever the flag appears; asks before `vercel`/`turso`), path-suffix matching for generated files, `.env*` blocked for Read too, destructive git commands denied, MCP servers pinned.
- **Known limit:** the hooks guard against accidents, not a determined agent (e.g. a Python one-liner reading `.env`).

### 26. B1: scaffold, split across two subagents
- **Brief:** backend + repo tooling (uv, FastAPI factory, settings, problem+json, request id, Alembic, pytest fixtures, Makefile, lefthook, CI) to one subagent; the Next.js 16 scaffold (shadcn, ESLint/Prettier, Vitest + MSW, Playwright, `/api` rewrite) to another in its own git worktree, against an agreed list of `package.json` script names. The orchestrator merged the halves, generated the API types and fixed one integration bug itself: with corepack enabled, `pnpm --dir frontend` run from the root ignores the `packageManager` pin, so the Makefile now runs pnpm from inside `frontend/`.
- **Subagent decisions:** health is a read-only `SELECT 1` (the write check belonged to the deferred deploy spike); statuses with no glossary slug (unhandled 500, health 503, 405) use `type: about:blank`; Python's sqlite3 runs with `autocommit=False` so a released SAVEPOINT can't commit the test transaction; tracebacks are logged without local variables; Next.js 16.4's Cache Components stay on (so the API status renders inside `<Suspense>`); `API_ORIGIN` must be set before `next build`, because the rewrite target is baked into the build.
- **⚠ correction (independent reviewer):** 17 findings, all verified by running code. The serious ones: a production start-up error printed `JWT_SECRET` and the Turso token (pydantic includes the input in the error); SQL errors would log bound values such as salaries; `make dev` used `wait -n`, which fails on macOS's bash 3.2; random-looking test secrets would trip gitleaks in CI; the test session used different autoflush/expire options from production; OpenAPI described 422 as FastAPI's default body instead of our problem+json; production accepted a non-empty `CORS_ORIGINS` with credentials; the coverage gate's `*` did not match nested files. All fixed test-first (bugs as `test: reproduce …` → `fix: …`), and the Turso SQLAlchemy dialect (`sqlalchemy-libsql`) was added with a no-network test that builds the production engine.
- **Process note:** one subagent's recursive grep printed lines of a local `backend/.env`; it held only the placeholder values copied from `.env.example`. Searches now exclude `.env` files.

### 27. B2: domain core (money, FX, stats, pay equity)
- **Brief:** the pure `domain/` layer test-first, with the behaviour list from [14](../14-testing-strategy.md) §5.1; stdlib only.
- **Subagent decisions:** trailing zeros are accepted (`"4500000.0"` JPY is ¥4,500,000, as XLSX numbers often arrive) while any non-zero digit past the currency's exponent is rejected; the mean is an exact integer half-even division; a non-full-time employee gets no compa-ratio (`not_full_time`) before the band is even looked up; `FxRate` refuses zero, negative and non-finite rates, so USD → USD is always the identity.
- **⚠ correction (independent reviewer):** `from_major` had no size limit: a 10-character cell `"1e10000000"` took 8 s and `"1e999999999"` hung, which on the import path is a denial of service, and `"1e30"` would overflow SQLite's 64-bit integer. `Decimal()` also accepted `"1_000"` and Arabic-Indic digits although the import doc rejects thousands separators. The pay-equity rollup lacked the mean, under/overpaid counts and the per-cohort view that the API needs, which would have pushed pay-equity rules into the service. A StrEnum identity check (`is not`) treated a plain `"FULL_TIME"` string from the DB as part-time.
- **Fix:** `MAX_AMOUNT_MINOR = 10**15 − 1` checked from the digits and exponent (hostile inputs now fail in milliseconds); a strict ASCII pattern for amounts typed as text; one `CompaRatioSummary` shared by `department_rollup` and a new `cohort_rollup`, plus `pay_equity_summary`; `!=` instead of `is not`. Each bug was reproduced by a failing test first.

### 28. B3: login, RBAC and audit events
- **Brief:** permissions and the role matrix, `users` + append-only `audit_events`, argon2 + JWT, `POST /auth/login|logout`, `GET /auth/me`, the login failure limit counted from audit events, and an authz-matrix test with a route-introspection guard.
- **Subagent decisions:** failed logins store `email_hash` = SHA-256 of the trimmed, lowercased email and no actor; the limit is checked before the password and applies to unknown emails too; a Bearer header wins over the cookie; tests use cheap argon2 parameters through an injected hasher (a test pins pwdlib's defaults for production); `as_role` mints the token directly, so tests don't create `auth.login` events.
- **⚠ correction (independent reviewer, with probe scripts):** a burst of 20 parallel wrong-password logins all passed the "5 failures" check, because a failure only counts once committed; the code used a sliding window although the glossary says "429 for 15 min"; bulk `UPDATE`/`DELETE` statements bypassed the append-only rule; the dummy hash for unknown emails was built lazily, so the first unknown-email login on a cold instance was measurably slower (a timing oracle); a user stored as `Admin@Acme.example` could never sign in; on a local SQLite file, concurrent read-then-write requests failed at once with "database is locked". Also a process slip: two small behaviours (UTC column type, Alembic render hook) arrived with their tests afterwards instead of first.
- **Fix:** re-check the limit after the password check (a burst now gets 5 real answers, then 429s); a fixed 15-minute block from the failure that reached the limit; an ORM listener refuses bulk updates/deletes of audit rows; the dummy hash is made at start-up; emails are normalised by the model; SQLite transactions start with `BEGIN IMMEDIATE`. Each bug reproduced by a failing test first.

### 29. B4: employees, salary history and masking
- **Brief:** reference tables, employees with append-only salary records and components, the employee endpoints (list with search/filters/sort/pagination, create with its `HIRE` record in one transaction, profile edit with optimistic locking, terminate/reactivate, salary changes, salary history), masking in the service, one audit event per mutation.
- **Orchestrator decision in the brief:** a salary range or salary sort must never compare raw amounts in different currencies. It works with exactly one currency, one country, or `salary_basis=usd` (USD bounds are turned into exact per-currency local bounds; the USD sort uses an integer key in SQL); otherwise `422`. The `{employee_id:int}` path converter keeps B7's `/employees/export` from being read as an id.
- **Subagent decisions:** unknown query parameters are a `422`; a no-op PATCH returns 200 without a new version or audit event; component amounts are money objects; a Viewer gets `403` for `salary_basis`/`comp` even without a range, and the whole `current_salary` is null for them.
- **⚠ correction (independent reviewer):** it re-ran every `test:` commit against the code before its `feat:` to prove the red step (all 39 failed as they should), checked the USD bound conversion against brute force over 250k cases (exact), and still found: after `ACME-999999` every create without a code failed for ever with a `409`; huge ids or page numbers caused a `500`; a component could be appended to an old salary record, breaking total = base + components; the Postgres migration silently skipped one foreign key; **a Viewer could tell when someone's pay changed, because the record `version` went up** (a privacy side channel the masking was meant to close); the search index was never used.
- **Fix:** all seven reproduced by failing tests first; `version` is now `null` for callers without `SALARY_READ`, and the Viewer guard test checks it.
- **Orchestration note:** to save wall-clock time, the frontend foundation (B8a) started right after B3, and B5, B7 and the employee screens (B8b) started on top of B4 while B4 was still under review, each in its own worktree. Merges still happen in block order.

### 30. B5: the deterministic 10k seed, and two user steers mid-build
- **Brief:** the seed in [12-seed-data.md](../12-seed-data.md): one seeded RNG, Faker per locale, anchor date 2026-10-01, bands from the pre-noise formula, salary history, the planted demo story, Core bulk inserts, `make seed` and `make seed-turso` (builds `build/seed.db` and only prints the `turso` command).
- **Result:** 10,000 employees, 24,058 salary records, 39,570 components, 1,360 bands, 300 terminated, in about 3.3 s locally; golden checksums over employees, records and components.
- **⚠ correction (independent reviewer):** the first golden checksum ignored names, dates and the whole salary history (changing a history probability still passed); the noise in the pay formula (σ = 0.12) flagged ~9 % of employees by itself, so the 175 planted outliers were only 18 % of the flags, and France Finance sat below the 0.95 threshold by chance; a Turso token in the environment crashed `--db-url sqlite:///…`; the "refuse a non-empty DB" check ran after the migration had already committed; rounding produced "Merit +0 %" records.
- **Fix:** wider goldens and exact counts; noise narrowed (σ = 0.06, redrawn outside [0.89, 1.12]) so that with the story off nobody is flagged, and with it on exactly the planted outliers are flagged and DE Customer Success (median 0.929) is the only department below threshold in any country; the other bugs reproduced by failing tests first.
- **User steers during the build:** "Dont worry too much about deko focus on only implementing working system first", then "No let styling polish as per design dont worry about deko story datas". The orchestrator first misread "deko" as decoration and told the frontend agent to skip polish, then corrected itself: styling stays polished to the design, and no more time goes into tuning the demo-story data (the noise fix above was already finished and green, so it was kept).

### 31. B6: insights and pay equity, and the privacy attacks the reviewer found
- **Brief:** the insight endpoints in scope (overview, by department, by job title, department cost, top earners, pay equity with cohorts/departments views and the cohort drill-down, pay bands, FX rates) plus the four privacy/correctness rules from the design review: `min`/`max` null for Viewers, differences computed from already-suppressed values, complementary suppression, no compa-ratio for non-full-time employees.
- **Result:** on the 10k seed, DE Customer Success shows a median compa-ratio of 0.93, the only department below the 0.95 threshold in any country, and exactly the 104 + 70 planted outliers are flagged. Service-level p95 is 8–275 ms.
- **⚠ correction (independent reviewer, with probe tests):** two working attacks let a Viewer recover one person's exact salary. (1) A one-person job role was hidden, but the complementary hide fell on a role in another department, so the department's total (shown by department cost) minus the visible role gave the salary to the cent. (2) Pay-equity cohorts hid a different set of role × level groups than the job-title breakdown, so the role total minus the visible level recovered the hidden one.
- **Fix:** one shared suppression rule over the full nesting country ⊃ department ⊃ job role ⊃ level (every parent has no hidden child or at least two), used by every endpoint that shows those groups; one privacy test per nesting, reproducing each attack first. docs/09 §2.8 lists the nestings and the limit that remains (combining different filters can still narrow a value).
- **Decision:** Viewers may filter insights by `status` (terminated included); the small-group rule still applies.

### 32. B7: CSV + XLSX import and export
- **Brief:** parsers → shared validator → duplicate checks → stored dry-run → all-or-nothing bulk commit with ids allocated in Python; template download; export with the list's exact filters, role-aware columns and formula escaping.
- **Orchestrator decisions in the brief:** "creator or an ADMIN" is checked as creator or `USER_ADMIN` holder (permissions, never role names), others get `404`; an unreadable or fake `.xlsx` is `400` (glossary over doc 14's `422`); the stored payload is cleared as soon as a job ends instead of a 7-day clean-up job.
- **Subagent decisions:** a fourth open dry-run expires the user's oldest one instead of returning `409` (dry-runs can't be deleted, so a `409` would lock a user out); a formula cell with no saved value refuses the upload; XLSX export budget 5 s locally (openpyxl alone needs ~2.5 s to write 10k rows).
- **⚠ correction (independent reviewer, with crafted files):** a 690 KB CSV with 100,000 header columns took 110 s (a quadratic duplicate check); a 5 KB XLSX with one cell at row 1,048,576 took 7–23 s; a 10k-row file with two bad cells per row produced a 10 MB error report, over Vercel's 4.5 MB response limit; array formulas slipped past the formula check; parsing ran while holding SQLite's write lock; the 4 MB cap was checked only after the whole body was spooled.
- **Fix:** header cap, blank-row cap, at most 500 stored errors with `errors_truncated` and `allowed_values` listed once per column, an early `Content-Length` check, parsing outside the transaction, and the generic 500 handler now logs the error type but never its message (it could carry names). Ids allocated in Python are documented as a SQLite/Turso-only assumption (Postgres is cut from v1).
