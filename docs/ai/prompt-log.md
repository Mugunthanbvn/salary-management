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
