# 00 — Assessment Brief & Expectations

What Incubyte asked for, what they say they evaluate, and where this repo answers each point. This is the **source of truth for requirements**: every other doc traces back here.

- **Status:** Reference
- **Last updated:** 2026-10-24
- **Sources:** the assessment document *"Salary Management Assessment – Candidates"* (kept locally, not committed) and Incubyte's invitation email for the **Software Craftsperson / Python / React / AI – III** role. Both are restated faithfully below.
- **Related:** [01-prd.md](01-prd.md) · [02-requirements-one-pager.md](02-requirements-one-pager.md) · [03-clarifications.md](03-clarifications.md) · [04-research.md](04-research.md) · [18-implementation-plan.md](18-implementation-plan.md)

---

## 1. The assessment (restated from the brief)

### 1.1 Framing
> This exercise is intentionally designed to assess how you think, design, and build software in an **AI-driven environment**. You are **required to use AI tools** to accelerate your work. We care about how you use them, the clarity of your thinking, and the quality of your engineering decisions.

**They expect the candidate to:**
- Demonstrate clarity in thought and structured problem solving.
- Show strong engineering fundamentals and product thinking.
- Make thoughtful architectural and design decisions.
- Write production-quality code and tests.
- Use AI intentionally while maintaining correctness and quality.
- **Make incremental commits** so they can understand how the solution evolved.

### 1.2 Goal
Build **employee salary management software** for an organization with **10,000 employees**.

### 1.3 User persona
**HR Manager** of the organization.

### 1.4 Problem statement
ACME org's HR team manages salary data for 10,000 employees **across multiple countries**, with everything kept in **Excel**, which is tedious. ACME wants the HR manager to **manage salary data via web-based software** and be able to **answer questions about how the org pays people**.

### 1.5 Requirements
- Write a **one-page requirements document before building the software**, outlining:
  - the goal,
  - scope & features,
  - **what you are deliberately leaving out, and the reasoning for it.**

### 1.6 Technical constraints
| Area | Constraint |
|---|---|
| Scope | **End-to-end, fully functional software**, including backend and UI |
| Backend | Language & framework **as per the role applied for** (preferred; Python here) or another of your choice. **Relational database** of your choice, e.g. SQLite |
| UI | **ReactJS or NextJS** (AngularJS for Java roles). **Component library** of your choice |
| Seeding | **Seed script with 10,000 employees** |
| Readiness | **Fully functional deployed software** + **a video demo** of the software |

### 1.7 Development approach
Use **agentic AI tools** of your choice to build the solution while keeping code quality and test coverage high. The solution should include:
- **A meaningful set of unit tests** covering the core functionality.
- Tests that are **fast, deterministic, and easy to understand**.
- **Good code structure, readability, and maintainability.**

The **commit history should show the evolution** of the solution through incremental commits.

### 1.8 Artifacts to commit
Commit any artifacts that help them understand your thinking and approach. Examples given (no required format):
- Requirements document
- Planning or design notes
- Architecture diagrams
- **Prompts or instructions used with AI tools**
- Trade-off explanations
- Performance considerations

### 1.9 How to succeed (their words)
The strongest submissions typically show:
- Clear thinking and structured problem solving
- Thoughtful architecture and design decisions
- Clean, maintainable code
- Meaningful tests
- Intentional use of AI tools
- Evidence of product thinking

> **"We are not looking for the most complex system, but for good engineering judgment."**

### 1.10 Submission
- Commit the code to a **Git repository**.
- Make sure the commits show the **development process**.
- Include **all the artifacts** above.
- **Reply to the same email** with the repository link when done.

---

## 2. Expectations from the invitation email

| Point | What they said | Implication for us |
|---|---|---|
| Why they assess this way | Good engineers think before coding, make pragmatic design decisions, build maintainable systems, use tools (including AI) intentionally, and show clear thinking, fundamentals and product thinking | Spec-first docs, ADRs, a prompt log |
| **Speed** | "If you submit the assignment in the least possible time, we will be able to prioritize your application." | 1–2 day build budget; v1 scope cut in the [docs README](README.md#v1-scope-decided-2026-10-24-read-this-first); further cuts in [18-implementation-plan.md](18-implementation-plan.md) §3a |
| **Ask, don't assume** | "If anything is unclear, please ask… Please do not make assumptions or proceed with doubts." | Questions + working assumptions + email draft: [03-clarifications.md](03-clarifications.md) |
| **Interview topics** after shortlisting | Your **design decisions**, **architecture**, **AI workflows**, **trade-offs** considered, **possible improvements** | Be able to walk through [05](05-architecture.md), [ADRs](adr/), [ai/workflow.md](ai/workflow.md), [20-trade-offs.md](20-trade-offs.md), and the "future work" sections |
| Walkthrough | "Please be prepared to walk us through your thinking and code." | The commit history + docs should tell the story without us present |

## 3. What Incubyte values (from their public material)
Researched in [04-research.md](04-research.md):
- **TDD is non-negotiable.** Their hiring blog says the take-home must be solved with **Test-Driven Development**. Their site says "the test defines done".
- **Spec before code.** The spec is "the contract" that keeps AI output from drifting.
- **AI as an amplifier of discipline.** Engineers review AI output as they would a colleague's work.
- **Clean code and continuous refactoring**, pairing, small frequent releases, XP practices.
- **Integrity, honesty and accountability** are non-negotiable. So the prompt log must be real (curated, not invented).

---

## 4. Requirement → where it's addressed

| # | Requirement (brief/email) | Our answer | Where |
|---|---|---|---|
| R1 | One-page requirements doc **before** building | Written first; it's the **first commit** in the repo | [02-requirements-one-pager.md](02-requirements-one-pager.md) |
| R2 | State what's **deliberately left out** and why | "Out of scope" section with reasons | [02](02-requirements-one-pager.md), [01-prd.md](01-prd.md) |
| R3 | HR manager can **manage salary data** on the web | Employee CRUD, salary changes with history, components | [01](01-prd.md), [07-api-spec.md](07-api-spec.md), [13-frontend-ux.md](13-frontend-ux.md) |
| R4 | **Answer questions about how the org pays people** | Insights (by country/department/title, department cost, top earners), pay equity vs pay bands, AI "Ask about pay" (if time allows) | [09-insights-pay-equity.md](09-insights-pay-equity.md), [10-ai-ask-design.md](10-ai-ask-design.md) |
| R5 | **Multiple countries** | 10 countries, each salary in its country's currency, USD reporting with a dated FX rate | [06-data-model.md](06-data-model.md), [ADR 0004](adr/0004-money-integer-minor-units.md), [ADR 0005](adr/0005-fx-read-time-conversion.md) |
| R6 | Replace **Excel** | CSV + XLSX import (dry-run, all-or-nothing) and export | [11-import-export.md](11-import-export.md) |
| R7 | **10,000 employees** | Indexed queries, performance budgets | [19-performance.md](19-performance.md) |
| R8 | Backend in the role's language + **relational DB** | FastAPI (Python) + SQLAlchemy + SQLite (Turso in prod) | [05-architecture.md](05-architecture.md), [ADR 0002](adr/0002-sqlite-everywhere-turso.md) |
| R9 | **React/Next.js UI** + component library | Next.js 16 + shadcn/ui | [13-frontend-ux.md](13-frontend-ux.md), [ADR 0017](adr/0017-toolchain.md) |
| R10 | **Seed script, 10,000 employees** | Deterministic seed (`--seed 42`) with realistic bands, history and a documented demo story | [12-seed-data.md](12-seed-data.md) |
| R11 | **Deployed**, fully functional | Vercel (web + API) + Turso, $0, deploy spike on day 1 | [17-deployment.md](17-deployment.md), [ADR 0016](adr/0016-deploy-vercel-turso.md) |
| R12 | **Video demo** | 4-minute script | [demo-script.md](demo-script.md) |
| R13 | **Use agentic AI tools**, intentionally | Claude Code with project rules, skills, reviewer agent, hooks, MCP | [16-claude-code-setup.md](16-claude-code-setup.md), [ai/workflow.md](ai/workflow.md) |
| R14 | **Meaningful unit tests** for core functionality | Domain/service/API tests; authorization matrix; import cases | [14-testing-strategy.md](14-testing-strategy.md) |
| R15 | Tests **fast, deterministic, easy to understand** | In-memory SQLite, fixed seeds, frozen time, a fake LLM, no network | [14-testing-strategy.md](14-testing-strategy.md) |
| R16 | **Code structure, readability, maintainability** | Layered modules, pure domain, lint + type gates | [05-architecture.md](05-architecture.md), [15-tooling-devex.md](15-tooling-devex.md) |
| R17 | **Incremental commits** showing evolution | TDD commit pairs (`test:` → `feat:` → `refactor:`), one short branch per build block, merge commits (no squash) | [14](14-testing-strategy.md), [15](15-tooling-devex.md), [18](18-implementation-plan.md) |
| R18 | Artifacts: requirements, design notes, architecture diagrams | This `docs/` folder (mermaid diagrams in 05/06) | [README.md](README.md) |
| R19 | Artifacts: **prompts used with AI** | Curated real prompt log + the review prompt | [ai/prompt-log.md](ai/prompt-log.md) |
| R20 | Artifacts: **trade-offs**, **performance** | Trade-offs doc + ADRs; performance budgets | [20-trade-offs.md](20-trade-offs.md), [adr/](adr/), [19-performance.md](19-performance.md) |
| R21 | **Product thinking** | Personas, currency-correct reporting, pay equity, privacy (masking, small groups), Excel migration path | [01-prd.md](01-prd.md), [08-security-rbac.md](08-security-rbac.md) |
| R22 | "Not the most complex system": **judgment** | Explicit exclusions, cut-first list, simple choices (SQLite, sync SQLAlchemy) | [02](02-requirements-one-pager.md), [20](20-trade-offs.md) |
| R23 | **Ask questions, don't assume** | Questions list + email draft | [03-clarifications.md](03-clarifications.md) |
| R24 | **Submit fast** | 1–2 day build budget, v1 scope cut, further-cut order | [README](README.md#v1-scope-decided-2026-10-24-read-this-first), [18-implementation-plan.md](18-implementation-plan.md) §3a |

---

## 5. Submission checklist
- [ ] Clarifying-questions email sent ([03](03-clarifications.md)) and answers logged
- [x] One-page requirements is the first commit (`docs: add one-page requirements`)
- [ ] Every build block is merged with a merge commit; history shows `test:` → `feat:` pairs (blocks B0–B8 so far; the insights and Ask screens are still being merged)
- [ ] `make verify` is green; CI is green on `main` (green locally on the release branch; CI on `main` not checked yet)
- [x] Seed runs: 10,000 employees, deterministic
- [ ] Deployed URL works for all three demo roles (Admin / HR Manager / Viewer)
- [ ] Video demo recorded and linked in the root README
- [ ] Root README: what it is, live URL, demo credentials, how to run locally, links to `docs/` (all but the live URL, which waits for the deployment)
- [x] Artifacts committed: requirements, design notes, diagrams, ADRs, prompt log, trade-offs, performance numbers (measured, not just targets; local only, deployed numbers pending)
- [ ] Tag `v1.0.0`
- [ ] **Reply to the same email** with the repository link
