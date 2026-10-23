# Demo Video Script

A proposed 3–5 minute script for the required video demo. It shows the product through the HR manager's eyes and covers the key engineering decisions in passing.

- **Status:** Draft for review (proposed; finalized in milestone 14)
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [11-import-export.md](11-import-export.md) · [12-seed-data.md](12-seed-data.md) · [13-frontend-ux.md](13-frontend-ux.md) · [17-deployment.md](17-deployment.md) · [18-implementation-plan.md](18-implementation-plan.md)

---

## Setup before recording

- Use the **deployed** app (Vercel + Turso), freshly reset to the deterministic seed ([17-deployment.md](17-deployment.md#63-reset-demo-data)), so the numbers match the seed story.
- Warm up the API first (open health once) to avoid a cold start on camera.
- Use a browser with a clean profile; zoom 110–125% for legibility; light theme (show dark mode briefly).
- Prepare `demo-import.csv`: 5 new employees, **1 deliberately bad row** (unknown job title) and **1 duplicate email**, plus a corrected copy.
- An Ask provider key is configured (Gemini default); the questions are rehearsed against the eval set.
- Screen recording at 1080p with a mic. Target length **4 minutes**, hard limit 5.

## Script

| # | Time | Screen / action | Narration (key points) |
|---|---|---|---|
| 1 | 0:00–0:20 | Title slide or README hero → login page | "ACME's HR team manages pay for 10,000 people in 10 countries in spreadsheets. This app replaces that and answers *how do we pay people?* Built with FastAPI, Next.js and SQLite, test-first." |
| 2 | 0:20–0:40 | Log in as **HR Manager** (`hr@acme.example`). Land on the Insights dashboard | Headcount, total payroll in USD with the FX date. "Per-country figures stay in local currency. We only convert to USD for cross-country views, at read time, with a dated rate." |
| 3 | 0:40–1:15 | **Employees** → search `müller` (Unicode) → filter Country = DE, Department = Customer Success → open one employee | Server-side pagination over 10k rows; filters live in the URL (copy the link). Detail page: salary timeline with snapshots ("L2 → L3, Promotion, +12%"), base + allowances + bonus target = total comp. |
| 4 | 1:15–1:45 | **Record salary change** → reason `MERIT`, +4%, effective today → save. Toast; the timeline shows a new entry | "History is append-only. Every change writes an audit event in the same transaction, and concurrent edits are caught with optimistic locking." |
| 5 | 1:45–2:30 | **Insights → Pay equity**, country DE. The department rollup shows **Customer Success** with a median compa-ratio ≈ **0.92** (badge: *systematically below band*), while other departments sit near 1.00. Drill into a cohort to see the band and the flagged employees | "Compa-ratio is base pay over the pay-band midpoint for the same role, level and country. Comparing against the band, not the team's own median, is what catches a whole team being underpaid. Here, German Customer Success is about 8% under band." (Mention that the seed plants this story, documented.) On the overview, toggle base ↔ total comp and annual ↔ monthly. |
| 6 | 2:30–3:05 | **Import** → upload `demo-import.csv` → dry-run preview shows row 3 *unknown job title* (with the allowed values) and row 5 *duplicate email* → upload the corrected file → commit → new employees appear | "HR's data lives in Excel, so import takes CSV or XLSX. A dry run validates every row first, then the commit is all-or-nothing, so a bad file never half-imports." Click Export → XLSX briefly. |
| 7 | 3:05–3:45 | **Ask about pay**: "Are we underpaying anyone in Germany?" → answer with figures, currency, FX date → expand **How I got this** (tools called) → follow-up: "And in India?" | "The model can only call read-only tools over the same insight services the dashboard uses, so the numbers match. It never writes SQL, and every tool respects the user's permissions." |
| 8 | 3:45–4:15 | Log out → log in as **Viewer** → Employees: salary columns masked, no edit actions → Insights: a tiny group shows "—" → Ask "Who are the top earners in the UK?" → access message | "Least privilege: a Viewer sees aggregates but not individual pay, and groups smaller than 5 are hidden, because an average over a handful of people can reveal someone's salary. The backend enforces this; the UI only hides." |
| 9 | 4:15–4:40 | Quick cuts: GitHub commit history (test: → feat: pairs), green CI checks, `docs/` folder (PRD, ADRs, prompt log) | "Every feature started with a failing test; you can see the pairs in the history. Decisions are in ADRs, and the prompt log shows how AI was used, including where it was wrong." |
| 10 | 4:40–4:50 | End card: deployed URL, repo URL, demo credentials note | "Thanks for watching." |

## Optional cut-ins (if time allows, or for a longer version)

- **Admin:** edit an FX rate → the USD totals on the dashboard change → the audit log shows who changed what.
- **Dark mode** toggle.
- **Phone viewport** of the employee list.
- **Conflict:** two tabs editing the same employee → the second save gets a clear "changed by someone else" message (409).

## Do and don't

- Do keep the narration product-first ("HR can now…") with engineering notes as one-liners.
- Do show real numbers from the deterministic seed; rehearse so they match [12-seed-data.md](12-seed-data.md).
- Don't show secrets, `.env` files, or the Vercel/Turso dashboards with tokens visible.
- Don't claim features that aren't built. If something was cut at a check-in, leave it out of the video.
