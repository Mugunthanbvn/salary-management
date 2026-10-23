# Clarifications & Assumptions

> Questions we would ask Incubyte before building, the assumption we take for each until answered, and a ready-to-send email.

- **Status:** Draft for review (email not yet sent — user to decide)
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [02-requirements-one-pager.md](02-requirements-one-pager.md) · [20-trade-offs.md](20-trade-offs.md)

---

The hiring email explicitly says: *"Ask Questions — Don't Assume."* We therefore list every material ambiguity. We proceed in parallel with documented assumptions, designed so that a different answer changes configuration or a small module — not the architecture.

## 1. Questions and working assumptions

| # | Question | Working assumption | Impact if different |
|---|---|---|---|
| Q1 | Are salaries stored in each employee's **local currency**, and should cross-country reports use a single reporting currency? | Local currency per employee (ISO 4217); USD as reporting currency using a static, dated FX table maintained by an Admin. | Reporting currency is a configuration value; FX source could be swapped for a live feed. |
| Q2 | Which **questions about pay** matter most to the HR manager? | Distribution and statistics by country, department, job title and level; total payroll; raises over time; pay-equity outliers. | Insight endpoints are modular; new ones reuse the same stats functions. |
| Q3 | Is salary **annual base** only, or should bonuses/allowances be included? | Annual base + allowances + target bonus (as components). Equity, commission and benefits excluded. | Components table can take more types. |
| Q4 | Do we need **salary history** (raises over time) or only the current salary? | Full append-only history with effective dates and reasons. | History can be hidden in UI if not wanted; no architecture change. |
| Q5 | What **employee attributes** are expected? | Employee code, name, email, job title (controlled list), department, level, employment type, country, status, hire/termination dates. No DOB, gender, address or bank details (data minimisation). | Additional fields are additive migrations. |
| Q6 | Is **authentication** expected, and how many roles? | Yes: Admin, HR Manager, Viewer, with permission-based checks; Viewer cannot see individual salaries. | Roles map to permissions in one place; easy to add/remove. |
| Q7 | Should HR be able to **import from Excel**? | Yes: CSV and XLSX import with dry-run preview and all-or-nothing commit; CSV/XLSX export. | Import could be dropped without affecting other modules. |
| Q8 | Is it acceptable to use **synthetic seed data** and share **demo credentials** for the deployed app? | Yes; synthetic data only; demo credentials in README for the demo environment; production mode refuses default secrets. | Credentials could be sent privately instead. |
| Q9 | Any expectations on **hosting** (cloud provider, cost)? | Free tier: Vercel (web + API) + Turso (hosted SQLite). | Code is portable; only deploy config changes. |
| Q10 | Is an **AI feature inside the product** welcome, and may we use a free LLM tier? | Yes, as a final milestone, feature-flagged; Gemini free tier by default (Groq alternative) because data is synthetic. | Feature can be disabled by removing the key. |
| Q11 | Should terminated employees appear in insights? | Excluded by default; included via filter. | Default filter value only. |
| Q12 | Should insights include part-time employees and contractors? | Full-time only by default; filter overrides. | Default filter value only. |
| Q13 | Expected **video demo** length/format? | **TBD** — plan for a ~5 minute screen recording following `demo-script.md`. | None. |
| Q14 | Preferred **relational database**? Brief mentions SQLite. | SQLite everywhere (Turso in production) via SQLAlchemy ORM; Postgres compatibility proven in CI. | Switch by `DATABASE_URL`. |
| Q15 | Does ACME have **pay bands** per role/level/country? | Yes, modelled as `pay_bands`. Compa-ratio = base ÷ band midpoint (the standard HR definition). Seeded bands come from our reference formula. | If ACME has real bands, they replace the seeded ones; no code change. |
| Q16 | Minimum group size before aggregates are hidden from read-only users? | 5 (common people-analytics threshold); HR Manager/Admin always see full figures. | One config constant (`MIN_GROUP_SIZE`). |
| Q17 | Should bulk import also **update** existing employees? | No: v1 is create-only; existing codes/emails are reported as duplicates. | Upsert is future work (merge rules + per-row locking). |
| Q18 | **Data retention / erasure** (audit log retention, GDPR-style deletion)? | Out of scope for the assessment; soft delete only, audit kept indefinitely. Documented. | A retention job + erasure workflow could be added later. |

## 2. Email draft (ready to send)

> **Subject:** Salary Management Assessment — a few clarifying questions
>
> Hi team,
>
> Thank you for the assessment. Before building, I'd like to confirm a few points. I'm proceeding with the assumptions below in the meantime and have designed the solution so that a different answer won't require rework.
>
> 1. **Currency** — I'm storing each salary in the employee's local currency and using USD (with a dated FX table) only for cross-country comparisons. Is that what you'd expect?
> 2. **Pay questions** — Are there specific questions the HR manager must be able to answer (e.g. median by country/role, pay equity, raises over time)?
> 3. **Compensation scope** — Should I model only base salary, or also allowances and bonus targets? I'm planning base + allowances + target bonus, excluding equity and commission.
> 4. **Salary history** — Is tracking salary changes over time (with reasons) in scope, or only the current salary?
> 5. **Access control** — I'm planning three roles (Admin, HR Manager, read-only Viewer) where the Viewer sees aggregates but not individual salaries. Is that reasonable?
> 6. **Excel import** — Since HR currently uses Excel, would CSV/XLSX import be valuable, or should I focus elsewhere?
> 7. **Demo access** — Is it acceptable to share demo credentials for the deployed app (synthetic data only)?
> 8. **AI** — Is a natural-language "ask about pay" feature inside the product welcome, and is a free LLM tier acceptable given the data is synthetic?
> 9. **Video demo** — Any preferred length or format?
>
> Thanks,
> **TBD (candidate name)**

## 3. Answers log

| Date | Question | Answer | Change made |
|---|---|---|---|
| — | — | *No answers yet* | — |
