# Research Notes

> What we learned before designing: what Incubyte values, what other candidates built, and the technology research behind each decision.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [20-trade-offs.md](20-trade-offs.md) · [15-tooling-devex.md](15-tooling-devex.md) · [17-deployment.md](17-deployment.md) · [ai/workflow.md](ai/workflow.md)

> **Method.** Research was done with AI-assisted web search and page fetching (October 2026), then cross-checked across sources. Many results were third-party blogs or aggregators; where sources disagreed, this is noted and the decision includes a verification step (e.g. the day-1 deploy spike). Versions are resolved at scaffold time, not trusted from articles.

---

## 1. What Incubyte expects

Sources: [Incubyte hiring process](https://blog.incubyte.co/blog/hiring-process/) · [incubyte.co](https://www.incubyte.co/) · job postings (aggregators) · [Incubyte "Bee" Claude Code plugin listing](https://claudepluginhub.com/plugins/incubyte-bee-bee)

| Signal | Evidence | How we respond |
|---|---|---|
| **TDD is mandatory** | Take-home must be solved with "Test Driven Development"; site: *"The test defines done, so the AI has a precise target and the output is verified, not just plausible."* | Red → green → refactor visible in commit history (`test:` then `feat:` commits); `/tdd` project skill. See [14-testing-strategy.md](14-testing-strategy.md). |
| **Spec before code** | Site: the spec is "the contract" that keeps AI output from drifting. Brief requires a one-page requirements doc first. | These docs, then [02-requirements-one-pager.md](02-requirements-one-pager.md) as first commit. |
| **AI as amplifier, verified** | *"AI compounds whatever a team already brings"*; engineers review AI output like a colleague's. Their Bee plugin encodes spec → plan → test → code. | Committed CLAUDE.md, rules, skills, reviewer agent, curated prompt log including where AI was wrong. See [16-claude-code-setup.md](16-claude-code-setup.md), [ai/workflow.md](ai/workflow.md). |
| **Clean code, refactoring, pairing, XP** | Postings: test-first, self-explanatory code, continuous refactoring, CI/CD, small frequent releases. | Layered architecture, strict typing, linting, CI, small commits, PR per milestone. |
| **Judgment over complexity** | Brief: *"We are not looking for the most complex system, but for good engineering judgment."* | Every decision has an ADR with alternatives; deliberate exclusions documented. |
| **Values** | "Integrity, honesty and accountability" are non-negotiable. | Prompt log uses real prompts only; known limitations stated openly. |
| **Interview topics** | Design decisions, architecture, AI workflows, trade-offs, improvements. | [20-trade-offs.md](20-trade-offs.md) and ADRs prepared for walkthrough. |

## 2. Competitor scan (public submissions of this assessment)

Search found ~9 public repositories implementing this brief. None are official Incubyte repos. Claims below are self-reported in READMEs and not independently verified.

| Repo | Stack / DB | Notable strengths | Gaps we observed |
|---|---|---|---|
| [youngboomer/incubyte-assessment](https://github.com/youngboomer/incubyte-assessment) ("CompPulse") | FastAPI (async SQLAlchemy) + Next.js; **SQLite** with FTS in a Docker volume | 192 commits; 305 backend + 91 web tests (~96 % coverage); pay changes with reasons; planning FX rates; hardened auth (scrypt, revocation, lockout); performance docs | Single shared login, no roles; no backup; demo credentials in README; self-hosted (reverse proxy) |
| [ritishbhardwaj/Incubyte-Employee-Salary-Management](https://github.com/ritishbhardwaj/Incubyte-Employee-Salary-Management) | FastAPI + React (Vite) + Neon Postgres | Compensation ledger; CSV import/export; deterministic seed; session + CSRF | Percentiles only verified on Postgres while tests run on SQLite; currency limited to USD in insights; default credentials in `.env.example`; Windows-only setup steps |
| [Chenthan/incubyte-salary-management](https://github.com/Chenthan/incubyte-salary-management) | Spring Boot + Angular + Postgres 17 | Decision register; money rules (no cross-currency sums); optimistic locking; Playwright + axe; random local credentials | Local only (not deployed); no salary history; single HR role; heavy setup |
| [kaushik552k/salary-management-system](https://github.com/kaushik552k/salary-management-system) | Node/Express + Next.js 14 | 10 countries, multi-currency analytics | Not inspected in depth |
| [snoopy2309/incubyte-salary-management](https://github.com/snoopy2309/incubyte-salary-management) | Java/Spring + React | — | Not inspected in depth |
| Others: [aryanagr](https://github.com/aryanagr/incubyte-salary-management), [soumyapokale](https://github.com/soumyapokale/incubyte-salary-management), [amankumar-19](https://github.com/amankumar-19/incubyte-engineering-assessment), [christaime](https://github.com/christaime/salary-management-incubyte) | Mixed | — | Not inspected in depth |

### Common gaps → our differentiators

| Common gap | Our answer |
|---|---|
| One shared login, no roles | Three roles mapped to permissions, salary masking, small-group rule ([08-security-rbac.md](08-security-rbac.md)) |
| Current salary only | Append-only history with reasons and title/level snapshot ([adr/0006-append-only-salary-history.md](adr/0006-append-only-salary-history.md)) |
| Weak or USD-only currency handling | Minor units + ISO 4217, read-time FX conversion with as-of date ([adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md), [adr/0005-fx-read-time-conversion.md](adr/0005-fx-read-time-conversion.md)) |
| Stats tested on one DB, run on another | Pure-Python stats + same SQLite dialect everywhere + Postgres CI job ([adr/0007-pure-python-stats.md](adr/0007-pure-python-stats.md)) |
| No AI in the product | "Ask about pay" via read-only tool calling ([10-ai-ask-design.md](10-ai-ask-design.md)) |
| No pay-equity analysis | Compa-ratio cohorts ([09-insights-pay-equity.md](09-insights-pay-equity.md)) |
| Often not deployed publicly | $0 always-on deployment ([17-deployment.md](17-deployment.md)) |

The bar is high (192 commits, 305 tests). We compete on **coherent design, correctness and explainability**, not on volume.

## 3. Money and multi-currency

Sources: [Handling currency values (DEV)](https://dev.to/cardinalby/handling-currency-values-facts-and-best-practices-3l81) · [Multi-currency money storage (subtracker)](https://subtracker.io/build/multi-currency-money-storage) · [Dinero.js: storing in a database](https://www.dinerojs.com/guides/storing-in-a-database) · [Storing money in MySQL](https://techearl.com/store-money-currency-mysql)

- Industry practice: store **integer minor units** plus **ISO 4217 currency code**; exponent varies per currency (JPY = 0, USD = 2, some = 3). Never floats.
- Alternative: fixed-point DECIMAL. Rejected for us because **SQLite has no true DECIMAL** (SQLAlchemy `Numeric` falls back to floating storage), so integers are the only portable exact type.
- Reject amounts with more decimals than the currency allows rather than rounding silently.
- **Convert at read time only**, attach the rate date, never persist converted values — otherwise historical totals shift when rates change.

→ [adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md), [adr/0005-fx-read-time-conversion.md](adr/0005-fx-read-time-conversion.md)

## 4. Database and hosting

### 4.1 Is SQLite suitable for 10,000 employees?
Yes. ~10k employees + ~30k salary records + ~40k components ≈ 5–10 MB. Indexed queries run in milliseconds; WAL mode allows concurrent reads; a single writer is adequate for a small HR team. The brief itself suggests SQLite, and the strongest competitor used it. The real constraint is **hosting**: SQLite needs a persistent disk.

### 4.2 Free hosting options (October 2026)

Sources: [Render: platforms with a real free tier](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026) · [Fly.io free tier 2026](https://www.saaspricepulse.com/blog/flyio-free-tier-2026) · [Railway alternatives](https://www.buildmvpfast.com/alternatives/railway) · [Free Docker hosting tested](https://snapdeploy.dev/blog/free-docker-hosting-2026-platforms-compared) · [Free FastAPI stack](https://agentdeals.dev/free-fastapi-stack) · [Vercel: ship a FastAPI app](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel) · [Vercel FastAPI boilerplate](https://vercel.com/templates/python/fastapi-python-boilerplate)

| Option | Free? | SQLite file persists? | Notes |
|---|---|---|---|
| Vercel (Python functions, zero-config FastAPI) | Yes | No (read-only FS) | Serverless; Hobby limits: 300 s max duration, ~4.5 MB body |
| Render free | Yes | No (no disk on free tier) | Sleeps when idle (~50 s wake) |
| Fly.io | No (trial: 2 VM-hours or 7 days, card required) | Yes (volumes) | ~$2–5/month |
| Railway | No (30-day trial, then $5/month Hobby) | Yes (volumes) | Trial could expire during review |
| Koyeb | Conflicting reports; card hold | Unverified | Not chosen |
| Self-hosted VM | Rejected by user (no own instances) | Yes | — |

### 4.3 Hosted databases

Sources: [Turso developer plan announcement](https://turso.tech/blog/turso-cloud-debuts-the-new-developer-plan) · [Turso free tier summary](https://agentdeals.dev/vendor/turso) · [Turso SQLAlchemy docs](https://docs.turso.tech/sdk/python/orm/sqlalchemy) · [sqlalchemy-libsql (archived)](https://github.com/libsql/sqlalchemy-libsql) · [tursodatabase/sqlalchemy-libsql](https://github.com/tursodatabase/sqlalchemy-libsql) · [Neon pricing](https://neon.com/pricing) · [Neon pricing explained](https://www.jetadmin.io/blog/neon-pricing/amp/)

| Service | Free tier (as reported) | Fit |
|---|---|---|
| **Turso** (hosted libSQL/SQLite) | ~100 DBs, 5 GB, 500M rows read / 10M rows written per month; no sleeping | **Chosen** — same SQLite dialect as local and tests. Risk: Python SQLAlchemy dialect is young (original repo archived June 2025; work continued in Turso's newer binding). |
| Neon (serverless Postgres) | 0.5 GB/project, ~100 CU-hours/month, scales to zero | **Fallback** — swap `DATABASE_URL`; portability proven by the Postgres CI job |

→ [adr/0002-sqlite-everywhere-turso.md](adr/0002-sqlite-everywhere-turso.md), [adr/0016-deploy-vercel-turso.md](adr/0016-deploy-vercel-turso.md)

### 4.4 Cross-site cookies
`*.vercel.app` is on the Public Suffix List, so two Vercel projects are different *sites*. A cookie set by the API project would be third-party from the web project's perspective; Safari and Firefox block those by default. Solution: a Next.js `rewrites` rule making `/api/*` same-origin. → [adr/0008-fastapi-auth-same-origin-rewrite.md](adr/0008-fastapi-auth-same-origin-rewrite.md)

## 5. Authentication libraries

Sources: [LogRocket: best auth library for Next.js 2026](https://blog.logrocket.com/best-auth-library-nextjs-2026/) · [MakerKit comparison](https://makerkit.dev/blog/tutorials/better-auth-vs-clerk) (vendor-biased)

- Auth.js (NextAuth v5) maintenance was taken over by the Better Auth team in September 2025 and is reportedly in security-patch mode; new projects are pointed to Better Auth.
- Both Auth.js and Better Auth want to own users inside Node/Next.js. Our authority for data and roles is FastAPI, and roles must be enforced (and tested) there.
- → FastAPI owns auth (pwdlib/argon2 + PyJWT), JWT in an httpOnly cookie, same-origin via rewrite.

## 6. LLM provider for "Ask about pay"

Sources: [Gemini API free tier limits](https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/) · [Gemini API pricing 2026](https://geotoolbox.ai/blog/gemini-api-pricing.md) · [Free LLM APIs compared (OpenRouter)](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) · [Groq free tier (BenchLM)](https://benchlm.ai/md/free-tier/groq.md)

| | Gemini free (AI Studio) | Groq free |
|---|---|---|
| Models | Flash-class only (Pro removed from free tier April 2026, reportedly) | Open models (e.g. gpt-oss-120b, Llama 3.3 70B) |
| Limits (reported) | ~15 RPM, ~1,500 requests/day; Google no longer publishes a fixed table | ~30 RPM, ~1,000 requests/day, ~6–12k tokens/min per organisation |
| Data use | **Free-tier prompts may be used to improve Google products** (except EU/UK/CH) | Reported not to train on API data (**verify at signup**) |
| API | OpenAI-compatible endpoint available | OpenAI-compatible |

Decision (user's choice): **Gemini default, Groq alternative**, via one OpenAI-compatible adapter. Synthetic data makes the free tier acceptable for the demo; a real deployment would require a paid/no-training tier. → [adr/0015-ai-ask-tool-calling.md](adr/0015-ai-ask-tool-calling.md)

## 7. Toolchain research

| Topic | Finding | Sources | Decision |
|---|---|---|---|
| Python type checker | Pyright ~98 % typing-spec conformance, same engine as VS Code Pylance; mypy mature but slower/less conformant; Pyrefly 1.0 (May 2026); ty still beta (0.0.x) | [danilchenko: ty vs mypy vs pyright](https://www.danilchenko.dev/posts/ty-vs-mypy-vs-pyright/) · [pydevtools: ty](https://pydevtools.com/handbook/topics/ty/) | Pyright strict |
| FastAPI version | Sources conflict (0.143.x vs 0.161.x in Oct 2026) | [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) | Resolve at scaffold |
| SQLAlchemy 2.1 | 2.1.0rc2 on 2026-09-08; requires Python ≥ 3.11 | [SQLAlchemy blog: 2.1.0rc2](https://www.sqlalchemy.org/blog/2026/09/08/sqlalchemy-2.1.0rc2-released/) | 2.0.x unless 2.1 final at scaffold |
| Next.js lint | Next 16 removed `next lint`; builds no longer lint | [Next.js 16 blog](https://nextjs.org/blog/next-16) · [Next ESLint docs](https://nextjs.org/docs/app/api-reference/config/eslint) | ESLint flat config in CI |
| Biome vs ESLint | Biome much faster; parity with Next and react-hooks rules unconfirmed | [Biome vs ESLint vs Oxlint](https://dev.to/royce_fabbd83cb268312e928/biome-vs-eslint-vs-oxlint-js-linters-2026-408h) | ESLint + Prettier |
| Frontend tests | Vitest + RTL for unit; Vitest cannot test async Server Components → Playwright | [Next.js Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest) | Vitest 4 + RTL + MSW + Playwright |
| Typed API client | openapi-typescript (types only) + openapi-fetch vs Hey API / Orval (full SDKs) | [Orval vs openapi-typescript vs Kubb](https://www.pkgpulse.com/guides/orval-vs-openapi-typescript-vs-kubb-openapi-client-2026) | openapi-typescript + openapi-fetch |
| Git hooks | pre-commit weak in monorepos; lefthook monorepo-aware, parallel; prek is new | [Lefthook git hooks](https://recca0120.github.io/en/2026/03/08/lefthook-git-hooks/) · [husky vs lefthook](https://www.pkgpulse.com/guides/husky-vs-lefthook-vs-lint-staged-git-hooks-nodejs-2026) | lefthook |
| Dependency bots | Renovate has stronger uv lock support; Dependabot built-in with some uv gaps | [uv: dependency bots](https://docs.astral.sh/uv/guides/integration/dependency-bots) | Dependabot (grouped monthly) |
| Claude Code practice | Keep CLAUDE.md short (<200 lines); deterministic rules → hooks; procedures → skills | [Claude Code best practices](https://code.claude.com/docs/en/best-practices) · [Steering Claude Code](https://claude.com/resources/articles/steering-claude-code-skills-hooks-rules-subagents-and-more) | See [16-claude-code-setup.md](16-claude-code-setup.md) |

Full rationale: [adr/0017-toolchain.md](adr/0017-toolchain.md), [15-tooling-devex.md](15-tooling-devex.md).

## 8. Design tooling

Sources: [Google Stitch MCP with Claude Code](https://pasqualepillitteri.it/en/news/647/google-stitch-mcp-export-claude-code-design-to-code) · [Claude Design / `/design` report](https://www.pingwest.com/w/316576) · [Impeccable](https://github.com/pbakaus/impeccable) · [Taste Skill](https://github.com/Leonxlnx/taste-skill) · [Hallmark](https://github.com/Nutlope/hallmark)

| Tool | What it is | Decision |
|---|---|---|
| Google Stitch | Gemini-based screen generator; exports `DESIGN.md` + MCP | Rejected: extra vendor; HTML output doesn't match shadcn |
| Claude Design / `/design` | Design canvases inside Claude (Anthropic Labs, 2026) | **Chosen** for screen exploration |
| frontend-design (official skill) | Guidance against templated UI | **Used** while coding |
| Impeccable | Anti-"AI slop" skill with deterministic anti-pattern rules; ~25k stars, Apache 2.0 | **Used** for per-screen audits; files reviewed before install |

→ [adr/0018-design-workflow.md](adr/0018-design-workflow.md), [13-frontend-ux.md](13-frontend-ux.md)

## 9. Open research items

- **TBD:** confirm Turso Python driver/dialect choice during the deploy spike.
- **TBD:** confirm Groq data-retention policy at signup.
- **TBD:** confirm exact FastAPI / Next.js / SQLAlchemy versions at scaffold time.
- **TBD:** confirm Claude Design `/design` availability in the user's Claude Code version.
