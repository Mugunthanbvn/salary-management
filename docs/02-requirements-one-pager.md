# Requirements — One Page

> The one-page requirements document the brief asks for, written before any code.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) (full detail) · [03-clarifications.md](03-clarifications.md) · [20-trade-offs.md](20-trade-offs.md)

---

## Goal
Replace ACME's Excel-based salary management with a web application that lets the **HR manager** maintain compensation data for **10,000 employees across 10 countries** and **answer questions about how the organisation pays people** — correctly across currencies, with history, and with access limited by role.

## Scope & features

| # | Feature | Why it matters |
|---|---|---|
| 1 | **Employee records** — create, view, edit, terminate/reactivate (soft delete); controlled job titles and departments | Single source of truth; clean data for analysis |
| 2 | **Search, filter, sort, paginate** — by name/ID, country, department, title, level, employment type, status, currency, salary range | Fast lookups at 10k scale; shareable URLs |
| 3 | **Salary history** — append-only records with effective date, reason, who changed it, and title/level snapshot | Answers "when and why did pay change?"; audit trail |
| 4 | **Compensation components** — base + allowances + target bonus; annual/monthly display | Base-only comparisons mislead across countries |
| 5 | **Multi-currency done right** — integer minor units + ISO 4217; per-country stats in local currency; USD reporting with FX date | Avoids the classic "summing rupees and dollars" error |
| 6 | **Insights** — headcount, payroll, min/max/mean/median/P25/P75 by country, department, title; distribution; department cost; raises; top/bottom earners | "How does the org pay people?" |
| 7 | **Pay equity** — compa-ratio vs pay band (title + level + country); flag < 0.8 / > 1.2; team-level "below band" view | Surfaces unfair pay |
| 8 | **Ask about pay (AI)** — plain-English questions answered by read-only tools over the same insight services | Fastest path from question to answer |
| 9 | **Import & export** — CSV/XLSX import with dry-run preview, per-row errors, duplicate detection, all-or-nothing commit; CSV/XLSX export | Migration path off Excel |
| 10 | **Roles & security** — Admin / HR Manager / Viewer; Viewer never sees individual salaries; aggregates over < 5 people hidden; audit log | Salary data is confidential |
| 11 | **Seed** — deterministic 10,000 employees with realistic bands and history | Required by brief; reproducible demos/tests |

## Deliberately left out — and why

| Left out | Reasoning |
|---|---|
| Payroll processing, tax, deductions | Different product (payroll engine); country-specific legal rules; not needed to answer pay questions |
| Equity/RSUs, commission, overtime, non-cash benefits | Complex valuation/variable rules; base + allowances + bonus target answer the brief's questions |
| Line-manager and employee self-service roles | Require a reporting hierarchy and employee accounts — large scope for little assessment value |
| Approval workflows, future-dated raises | Workflow engine scope; current-dated changes cover the HR manager's need |
| SSO / MFA, multi-tenancy | Single organisation, single small HR team; documented as future work |
| Live FX feeds | Static, dated, admin-maintained table is transparent and deterministic |
| Gender/demographic pay-gap analysis | Requires sensitive personal data and legal review; we minimise personal data instead |
| Custom backup system | Platform provides point-in-time restore (Turso); documented |

**Principle:** depth over breadth — fewer features, each correct, tested and explainable.
