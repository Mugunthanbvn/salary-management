# ACME Salary Management: Documentation

Design and planning documents for the ACME Salary Management system (Incubyte Software Craftsperson take-home assessment). All of these were written **before any code**, in line with the "spec before code" approach.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Product in one line:** a web app that lets ACME's HR team manage salary data for 10,000 employees across 10 countries, replacing their Excel workflow, and answer "how does the org pay people?" with correct multi-currency insights, pay-equity analysis and a natural-language "Ask about pay" assistant.

---

## v1 scope (decided 2026-10-24): read this first

The build budget is **1–2 days** (Incubyte prioritises fast submissions, [00](00-assessment-brief.md) §2). The docs below were written for a larger plan. The items in this table are **cut from v1**. Where a doc still describes them, read that section as a future-work design, not as something that was built.

| Cut from v1 | What v1 does instead | Docs that describe the cut item |
|---|---|---|
| Postgres portability CI job (`backend-pg`, `compose.yaml`) | SQLite-only CI. Neon stays the fallback if the deploy spike fails | [14](14-testing-strategy.md) §8, [15](15-tooling-devex.md) §8, [ADR 0002](adr/0002-sqlite-everywhere-turso.md) |
| Claude Design phase (milestone 7b) | One time-boxed **Claude Design** canvas instead of a phase: 6 desktop + 3 phone screens ([design/claude](design/claude/README.md)), rules in [design/DESIGN.md](design/DESIGN.md), then shadcn/ui | [13](13-frontend-ux.md) §5, [ADR 0018](adr/0018-design-workflow.md) |
| The whole admin UI (users, FX rates, countries, audit log viewer) | Users, FX rates and countries are seeded. Audit events are still written and tested | [13](13-frontend-ux.md) §4.9, [07](07-api-spec.md) §9–11 |
| Raises insight | Not built | [09](09-insights-pay-equity.md) §3.7, [07](07-api-spec.md) §8.9 |
| Salary distribution histogram | Not built | [09](09-insights-pay-equity.md) §3.4, [07](07-api-spec.md) §8.6 |
| Groq provider run and the model comparison table | Gemini only; small eval set | [10](10-ai-ask-design.md) §11, [ADR 0015](adr/0015-ai-ask-tool-calling.md) |
| Dependabot, CodeQL, knip | Not set up | [15](15-tooling-devex.md) §8, §11 |
| Most Playwright tests | At most one smoke flow | [14](14-testing-strategy.md) §5.8 |
| Preview deployments | Production only; everything else is tested locally | [17](17-deployment.md) §3.1, §4, §7 |
| Salary in a currency other than the country's | Every salary is in its country's currency (enforced by validation). A country change goes through a salary change | [06](06-data-model.md) §4.2, §4.6, [09](09-insights-pay-equity.md) §4 |

**Kept in full:** CSV + XLSX import (dry-run, all-or-nothing commit) and CSV/XLSX export ([11](11-import-export.md)), because HR's data lives in Excel.

**Never cut:** TDD (`test:` → `feat:` commits), the one-pager, the 10k seed, employees + salary history, currency-correct insights, band-based pay equity, RBAC with Viewer masking, the deployed app, the video demo.

The day-by-day build order is in [18 — Implementation plan](18-implementation-plan.md). Canonical names, enums, error codes and numbers are in the [glossary](glossary.md): if a doc disagrees with it, the glossary wins.

---

## Suggested reading order

| If you want to… | Read |
|---|---|
| Know what Incubyte asked for and expects | [00 — Assessment brief & expectations](00-assessment-brief.md) |
| Understand the product in 2 minutes | [02 — Requirements one-pager](02-requirements-one-pager.md) |
| See the full product spec | [01 — PRD](01-prd.md) → [03 — Clarifications](03-clarifications.md) |
| Understand the system design | [05 — Architecture](05-architecture.md) → [06 — Data model](06-data-model.md) → [07 — API spec](07-api-spec.md) → [08 — Security & RBAC](08-security-rbac.md) |
| Understand the features in depth | [09 — Insights & pay equity](09-insights-pay-equity.md) → [10 — AI "Ask about pay"](10-ai-ask-design.md) → [11 — Import/Export](11-import-export.md) → [12 — Seed data](12-seed-data.md) → [13 — Frontend & UX](13-frontend-ux.md) |
| Understand how it will be built | [14 — Testing strategy](14-testing-strategy.md) → [15 — Tooling & DevEx](15-tooling-devex.md) → [16 — Claude Code setup](16-claude-code-setup.md) → [17 — Deployment](17-deployment.md) → [18 — Implementation plan](18-implementation-plan.md) |
| See the reasoning behind each decision | [20 — Trade-offs](20-trade-offs.md) + [ADRs](adr/) |
| See how AI was used | [AI workflow](ai/workflow.md) + [Prompt log](ai/prompt-log.md) |

---

## Document index

### Product
| # | Document | Purpose |
|---|---|---|
| — | [Glossary](glossary.md) | Canonical names, enums, audit actions, error codes, env vars and numbers; wins over any other doc |
| 00 | [Assessment brief & expectations](00-assessment-brief.md) | The brief restated, the email's expectations, a map from each requirement to the doc that covers it, and a submission checklist |
| 01 | [PRD](01-prd.md) | Problem, personas, goals and non-goals, user stories with acceptance criteria, functional and non-functional requirements, success metrics, risks |
| 02 | [Requirements one-pager](02-requirements-one-pager.md) | The one-page requirements document the brief asks for: goal, scope, what's deliberately left out and why |
| 03 | [Clarifications](03-clarifications.md) | Open questions for Incubyte, the assumptions taken, and an email draft |
| 04 | [Research](04-research.md) | What Incubyte values, a scan of competing submissions, and hosting/DB/auth/LLM/tooling research with sources |

### Design
| # | Document | Purpose |
|---|---|---|
| 05 | [Architecture](05-architecture.md) | System context and containers, request flow, same-origin auth, layering, module map, serverless constraints |
| 06 | [Data model](06-data-model.md) | ERD, tables, constraints, indexes, money and FX rules, salary history, audit |
| 07 | [API spec](07-api-spec.md) | Every endpoint with its permission, schemas, examples and error format |
| 08 | [Security & RBAC](08-security-rbac.md) | Permission matrix, masking, small-group rule, auth details, threat model |
| 09 | [Insights & pay equity](09-insights-pay-equity.md) | Every metric and its formula, currency-context rules, compa-ratio |
| 10 | [AI "Ask about pay"](10-ai-ask-design.md) | Natural-language Q&A over read-only insight tools, guardrails, providers, evals |
| 11 | [Import / Export](11-import-export.md) | CSV + XLSX import with dry-run, all-or-nothing commit, and role-aware export |
| 12 | [Seed data](12-seed-data.md) | Deterministic 10k-employee dataset, salary bands, history, the planted demo story |
| 13 | [Frontend & UX](13-frontend-ux.md) | Screens, navigation, role-aware UI, money formatting, design workflow, accessibility |

### Engineering
| # | Document | Purpose |
|---|---|---|
| 14 | [Testing strategy](14-testing-strategy.md) | TDD workflow, test pyramid, determinism, coverage gates, e2e, AI evals |
| 15 | [Tooling & DevEx](15-tooling-devex.md) | Every tool explained, Makefile, git hooks, CI, GitHub policies |
| 16 | [Claude Code setup](16-claude-code-setup.md) | CLAUDE.md, rules, skills, reviewer agent, hooks, MCP servers |
| 17 | [Deployment](17-deployment.md) | Vercel (web + API) + Turso, env vars, migrations/seed, fallback, deploy spike |
| 18 | [Implementation plan](18-implementation-plan.md) | The 2-day build order with done-criteria, further cuts and risks |
| 19 | [Performance](19-performance.md) | Budgets, indexes, scaling path |
| 20 | [Trade-offs](20-trade-offs.md) | Major choices compared with the alternatives |
| — | [Demo script](demo-script.md) | Script for the 3–5 minute demo video |
| — | [Handoff](handoff.md) | What is done, what is pending (deployment), and the decisions taken |

### Decisions (ADRs)
| ADR | Decision |
|---|---|
| [0000](adr/0000-template.md) | Template |
| [0001](adr/0001-monorepo.md) | Monorepo layout |
| [0002](adr/0002-sqlite-everywhere-turso.md) | SQLite everywhere, Turso in production |
| [0003](adr/0003-sync-sqlalchemy-serverless.md) | Synchronous SQLAlchemy on serverless |
| [0004](adr/0004-money-integer-minor-units.md) | Money as integer minor units + ISO 4217 |
| [0005](adr/0005-fx-read-time-conversion.md) | FX conversion at read time only |
| [0006](adr/0006-append-only-salary-history.md) | Append-only salary history |
| [0007](adr/0007-pure-python-stats.md) | Statistics as pure Python domain functions |
| [0008](adr/0008-fastapi-auth-same-origin-rewrite.md) | FastAPI-owned auth, same origin via Next.js rewrite |
| [0009](adr/0009-permission-rbac-small-group-rule.md) | Permission-based RBAC + small-group rule |
| [0010](adr/0010-compensation-components.md) | Compensation components (base + allowances + bonus target) |
| [0011](adr/0011-audit-events.md) | Append-only audit events |
| [0012](adr/0012-bulk-import-dry-run.md) | Bulk import with dry-run, all-or-nothing commit |
| [0013](adr/0013-soft-delete-optimistic-locking.md) | Soft delete + optimistic locking |
| [0014](adr/0014-contract-first-openapi-client.md) | Contract-first typed API client |
| [0015](adr/0015-ai-ask-tool-calling.md) | AI Ask via tool calling (Gemini default, Groq alternative) |
| [0016](adr/0016-deploy-vercel-turso.md) | Free deployment on Vercel + Turso |
| [0017](adr/0017-toolchain.md) | Toolchain choices |
| [0018](adr/0018-design-workflow.md) | Design workflow (Claude Design + Impeccable) |
| [0019](adr/0019-vercel-services-single-project.md) | One Vercel project with services (backend + frontend) |

### AI
| Document | Purpose |
|---|---|
| [AI workflow](ai/workflow.md) | How AI is used in each phase and how its output is verified |
| [Prompt log](ai/prompt-log.md) | Curated log of the real prompts and decisions from planning |
| [Evals](ai/evals/README.md) | Evaluation set for the Ask feature |

### Created later (placeholders)
| Path | When |
|---|---|
| `design/DESIGN.md` (short, optional) | Day 2, frontend block |
| `ai/evals/ask.yaml` + results | Day 2, if Ask is built |

---

## Decisions made after the first draft (2026-10-24)
These came up while writing the docs and have been decided and applied to every affected doc.

| # | Topic | Decision | Why | Where |
|---|---|---|---|---|
| 1 | **Pay-equity benchmark** | Add `pay_bands` (job role × level × country → min/mid/max). Compa-ratio = **base ÷ band midpoint**. Add a **department rollup** (median compa-ratio per department × country, flagged below 0.95). Cohort P25/median/P75 stays as context. | The first draft compared people with their own cohort median. A team-wide gap moves that median too, so systemic underpayment (the planted DE Customer Success −8%) would be invisible. Band-based compa-ratio is the standard HR definition. | [09](09-insights-pay-equity.md) §3.8, [06](06-data-model.md) §4.8a, [07](07-api-spec.md) §8.10–8.12, [12](12-seed-data.md) §8, [13](13-frontend-ux.md) §4.3 |
| 2 | Small-group threshold | **n < 5** hidden for Viewers | Common people-analytics threshold; HR/Admin still see everything | [08](08-security-rbac.md) §4.2, [ADR 0009](adr/0009-permission-rbac-small-group-rule.md) |
| 3 | Import behaviour | **Create-only** in v1 | Upsert needs per-field merge rules and per-row locking; future work | [11](11-import-export.md) |
| 4 | Session policy | 8 h JWT, no refresh token; lockout after 5 failed logins for 15 min | Simple and safe for an internal tool | [08](08-security-rbac.md) |
| 5 | Retention / erasure | Out of scope, documented | Not needed to demonstrate the product; flagged for real-world use | [03](03-clarifications.md) Q18 |
| 6 | Seed: Singapore names | Curated Chinese/Malay/Indian name lists in the seed config | Faker has no `en_SG`; a fixed list is realistic and deterministic | [12](12-seed-data.md) §9 |
| 7 | **v1 scope cut** | Cut the items in "v1 scope" above | 1–2 day build budget; a hostile design review flagged the scope as too large for a fast submission | This README, [02](02-requirements-one-pager.md), [18](18-implementation-plan.md) |
| 8 | Salary currency | Always the country's currency | That's how local hires are paid in practice. Allowing other currencies made compa-ratio divide, say, a USD salary by a EUR band | [06](06-data-model.md) §4.2 |

**Still open, by design (resolved in the day-1 deploy spike):** the Turso SQLAlchemy dialect/URL, the Vercel Python entrypoint key, cookie forwarding, the exact Gemini model ID and the project's real Gemini free-tier quota. See [17](17-deployment.md), [ADR 0002](adr/0002-sqlite-everywhere-turso.md), [ADR 0015](adr/0015-ai-ask-tool-calling.md).

---

## Conventions
- **(proposed)** means a sensible default chosen to keep the docs concrete; open to change during review.
- **TBD** means not yet decided; resolved at the milestone shown in [18 — Implementation plan](18-implementation-plan.md).
- Exact package versions are resolved at scaffold time and pinned in lockfiles ([ADR 0017](adr/0017-toolchain.md)).
- Permission names (`EMPLOYEE_READ`, `SALARY_READ`, …), enums, audit actions, error codes and env vars are defined once, in the [glossary](glossary.md).
