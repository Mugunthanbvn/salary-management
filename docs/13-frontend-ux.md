# 13 — Frontend & UX

> **Purpose:** Describe the web app from the user's side: information architecture, every screen and what it contains, role-aware behaviour, URL state, money formatting, the design workflow (Claude Design → DESIGN.md → Impeccable audit), visual direction, and accessibility.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [05-architecture.md](05-architecture.md) · [07-api-spec.md](07-api-spec.md) · [08-security-rbac.md](08-security-rbac.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [11-import-export.md](11-import-export.md) · [14-testing-strategy.md](14-testing-strategy.md) · [16-claude-code-setup.md](16-claude-code-setup.md) · [adr/0008-fastapi-auth-same-origin-rewrite.md](adr/0008-fastapi-auth-same-origin-rewrite.md) · [adr/0014-contract-first-openapi-client.md](adr/0014-contract-first-openapi-client.md) · [adr/0018-design-workflow.md](adr/0018-design-workflow.md)

---

## 1. Users and their jobs

| Persona | Role | Main jobs in the UI |
|---|---|---|
| **Hema**, HR Manager | `HR_MANAGER` | Find an employee fast; update details; record a raise or promotion; import new hires from Excel; answer leadership's pay questions; spot unfair pay |
| **Arun**, HR systems admin | `ADMIN` | Everything Hema does, plus manage users and roles, FX rates, countries, and review the audit log |
| **Farah**, Finance / leadership | `VIEWER` | See how the org pays (aggregates, distributions, pay equity), export headcount lists, ask questions. **Never sees individual salaries** |

Design consequence: this is a **data-dense internal tool used daily**. Speed, legibility of numbers, and trust ("is this figure in EUR or USD?") matter more than visual flair.

## 2. Information architecture

```
┌──────────────────────────────────────────────────────────────┐
│ ACME Pay   [Insights] [Employees] [Ask] [Admin ▾]   Hema ▾   │  ← top bar (Admin only for ADMIN; Ask hidden if feature off)
├──────────────────────────────────────────────────────────────┤
│ page content                                                 │
└──────────────────────────────────────────────────────────────┘
```

| Route | Screen | Visible to |
|---|---|---|
| `/login` | Sign in | everyone (unauthenticated) |
| `/` | → redirects to `/insights` | — |
| `/insights` | **Insights dashboard** (org overview) | all roles (`INSIGHTS_READ`) |
| `/insights/pay-equity` | **Pay equity** | all roles; drill-down to individuals needs `SALARY_READ` |
| `/employees` | **Employee directory** | all roles (`EMPLOYEE_READ`); salary columns need `SALARY_READ` |
| `/employees/new` | Create employee | `EMPLOYEE_WRITE` |
| `/employees/[id]` | **Employee detail** + salary timeline | all roles; salary sections need `SALARY_READ` |
| `/employees/import` | **Import** (upload → preview → commit) | `IMPORT` |
| `/ask` | **Ask about pay** | `ASK` and feature enabled |
| `/admin/users` | Users & roles (**cut from v1**) | `USER_ADMIN` |
| `/admin/fx-rates` | FX rates (**cut from v1**) | `FX_ADMIN` |
| `/admin/countries` | Countries (default currency) (**cut from v1**) | `REFERENCE_ADMIN` |
| `/admin/audit` | Audit log (**cut from v1**) | `AUDIT_READ` |

Navigation is a **top bar** (proposed). Insights is the landing page, because the problem statement centres on "answering questions about how the org pays people".

**Auth redirect:** `proxy.ts` (Next 16's middleware) redirects unauthenticated requests to `/login?next=…`. Routes the user's permissions don't allow show a 403 page with a link home. The **backend is the enforcement point**; the UI only hides things ([08-security-rbac.md](08-security-rbac.md)).

## 3. Global UI patterns

### 3.1 Data loading and mutations

- **Server Components** fetch data on the server through a typed `openapi-fetch` client, forwarding the auth cookie. First paint arrives with data, with no client fetch waterfall ([adr/0008-fastapi-auth-same-origin-rewrite.md](adr/0008-fastapi-auth-same-origin-rewrite.md)).
- **Server Actions** handle mutations, followed by `revalidatePath`. Optimistic locking conflicts (`409`) show a dialog: "This employee was changed by someone else. Reload to see their changes."
- Toasts (sonner) confirm success; errors show the problem+json `detail` message in plain language.
- Loading: route-level `loading.tsx` skeletons that match the final layout (no layout shift).

### 3.2 URL as state (nuqs)

All filter, sort, and paging state lives in the **URL query string**, managed with `nuqs`:

```
/employees?q=müller&country=DE&department_id=1&level=L3&status=ACTIVE&sort=-current_base&page=2&page_size=25
/insights?country=DE&comp=total&period=monthly
/insights/pay-equity?country=DE&department_id=4
```

URL parameters use the API's names ([glossary](glossary.md) §6), so a page URL maps straight onto its API call. `period` is the one UI-only parameter. Benefits: links can be shared ("look at this view"), the back and forward buttons work, refresh keeps state, and the Ask feature's **"View in dashboard"** link is just a URL ([10-ai-ask-design.md](10-ai-ask-design.md)).

Paging defaults: **page size 25**, options 25 / 50 / 100 (max 100) ([07-api-spec.md](07-api-spec.md)).

### 3.3 Money formatting rules

| Rule | Detail |
|---|---|
| Source | The API returns `{ amount_minor, currency }`. The UI never receives floats |
| Formatter | One utility, `formatMoney(amountMinor, currency, { period, compact })`, that uses `Intl.NumberFormat` with `style: "currency"` and the **currency's minor-unit exponent** (JPY 0, others 2) |
| No float maths | Conversion to a display number uses `BigInt`/string arithmetic for the major/minor split. Monthly display is (annual ÷ 12), rounded half-even at the minor unit, **display only** |
| Currency always visible | Every amount shows its currency (code or symbol + code where ambiguous, e.g. `$` for USD vs CAD vs AUD → `US$`, `CA$`, `A$`) |
| USD conversions | Shown as a secondary value, e.g. `€52,000 · ≈ US$56,160`, with a tooltip: "FX as of 2026-10-01 (illustrative)" |
| Locale | Number grouping follows the user's browser locale by default. **(Proposed)** India-specific lakh grouping (`₹22,20,000`) when the currency is INR, via the `en-IN` locale |
| Tabular figures | All numeric table cells use `font-variant-numeric: tabular-nums` and right alignment, so digits line up |
| Compact mode | Charts and KPI tiles may use compact notation (`€1.2M`); tables always show full values |

Unit tests cover JPY (no decimals), INR grouping, negative-free inputs, BigInt-sized amounts, and monthly rounding ([14-testing-strategy.md](14-testing-strategy.md)).

### 3.4 Global toggles: comp basis and period

Shown on all insight screens and on the employee list (salary columns):

- **Base | Total comp**: maps to the `comp=base|total` API parameter ([09-insights-pay-equity.md](09-insights-pay-equity.md) §2.2). The tooltip explains: "Total = base + allowances + target bonus. Equity and commission are not included."
- **Annual | Monthly**: client-side display only (`period` URL param).
- **Population chip**: "Full-time · Active". Click to change employment type or status. Makes the default visible ([09-insights-pay-equity.md](09-insights-pay-equity.md) §2.1).

### 3.5 Role-aware UI

| Element | HR_MANAGER / ADMIN | VIEWER |
|---|---|---|
| Salary columns in the employee list | Shown | Hidden (column absent; the API returns salary fields as `null` with `"salary_masked": true`) |
| Salary-range filter, sort by salary | Shown | Hidden (API returns `403`) |
| Employee detail: compensation + timeline | Shown | Replaced by a neutral note: "Compensation details are restricted for your role" |
| Create / edit / terminate / record change buttons | Shown | Hidden |
| Import | Shown | Hidden |
| Export | With salaries | Without salaries; the button label says "Export (no salary data)" |
| Small groups in insights | Values shown | Values **and headcount** shown as "—" with tooltip "Hidden to protect individual pay (fewer than 5 people)" |
| Pay-equity drill-down to names | Shown | Hidden; cohort counts only |
| Admin menu | ADMIN only | Hidden |

The permission set comes from `GET /api/v1/auth/me` (`permissions[]`, `features{}`). Components check **permissions**, not role names ([adr/0009-permission-rbac-small-group-rule.md](adr/0009-permission-rbac-small-group-rule.md)).

### 3.6 Empty, loading and error states

Every screen defines:

- **Empty:** a friendly explanation plus the next action, e.g. "No employees match these filters" with a "Clear filters" button.
- **Loading:** a skeleton matching the layout.
- **Error:** problem+json `title`/`detail`, a "Try again" button, and a request ID for support (from the `X-Request-ID` header).
- **Forbidden:** "You don't have access to this" (never a blank page).

---

## 4. Screens

### 4.1 Login (`/login`)

- Email and password fields, a "Sign in" button, and the error "Email or password is incorrect" (no hint about which one).
- After login, redirect to `next` or `/insights`.
- The demo environment shows a small banner with the three demo accounts (Hema, Arun, Farah), **demo deployment only** (env flag), so reviewers can try each role ([12-seed-data.md](12-seed-data.md) §11).

### 4.2 Insights dashboard (`/insights`)

**Question it answers:** "How does the org pay people, at a glance?"

| Area | Content |
|---|---|
| Header | Title, global toggles (Base/Total, Annual/Monthly), population chip, filters: country, department, job role, level |
| KPI tiles | Headcount · Total annual payroll (USD) · Median pay (USD, org-wide) · Countries · FX as-of date |
| **Pay by country** table | Country, headcount, min, P25, **median**, mean, P75, max in **local currency**, plus a USD median column; sortable; a row click filters the dashboard to that country |
| **Salary distribution** chart (**cut from v1**) | Histogram (local currency when one country is selected, otherwise USD, with a visible label); P25, median, and P75 reference lines |
| **Pay by department** | Bar chart of median (and mean on hover). Currency label follows the single- or mixed-currency rule |
| **Department cost** | Horizontal bar of total payroll in USD with share-of-total % |
| **Raises** (**cut from v1**) | Date-range picker (default: last 12 months); average raise % by department; stacked count by reason (Merit / Promotion / Market adjustment / Correction) |
| **Top / bottom earners** (HR/Admin) | Country selector (required), top 10 / bottom 10 table with links to employees |
| Links | "Open pay equity →" · "Ask a question →" |

Rules: when a group mixes currencies, the section header shows a **"USD"** badge with the FX tooltip. Local-currency sections show the currency code in the header.

### 4.3 Pay equity (`/insights/pay-equity`)

**Question it answers:** "Are we paying people fairly against the pay band for their job, and is any team systematically below band?"

| Area | Content |
|---|---|
| Explainer (collapsible) | "Compa-ratio = base pay ÷ the midpoint of the pay band for the same role, level and country. Below 0.8 is under the band minimum (may be underpaid); above 1.2 is over the band maximum." |
| Filters | Country (recommended), department, job role, level. The Base/Total toggle is disabled here (tooltip: "Pay bands are defined on base salary") |
| Summary tiles | Employees evaluated · Employees below band · Employees above band · Departments below threshold |
| **Cohort table** | Role · Level · Country · Headcount · P25 · Median · P75 · Band min/mid/max (local currency) · Median compa-ratio · # underpaid · # overpaid. Sort by most flagged. A spread bar shows P25–P75 and the median tick drawn over the band (min–max shaded, mid marked) |
| **Department rollup** (shown first) | Bar chart + table: median compa-ratio per department in the selected country, with a reference line at 1.00 and a threshold line at 0.95. Departments below 0.95 get a "Systematically below band" badge ([09-insights-pay-equity.md](09-insights-pay-equity.md) §3.8) |
| **Drill-down** (HR/Admin) | Click a cohort → flagged employees: name, code, pay, band, compa-ratio badge (red < 0.8, amber > 1.2), link to the employee |
| Viewer | Department rollup + cohort table (no drill-down); groups with < 5 people suppressed; band values visible |

### 4.4 Employee directory (`/employees`)

**Question it answers:** "Find someone / a set of people, fast."

| Area | Content |
|---|---|
| Toolbar | Search box (name, employee code, email; debounced 300 ms; **case- and accent-insensitive**: `muller` finds `Müller` and `jose` finds `José`, via the backend's lowercased, accent-stripped `search_text`); filter chips: country, department, job role, level, status, employment type, currency, salary range (enabled only once a currency is chosen, or with "compare in USD"). **For Viewers, the salary-range filter and sorting by salary are not shown** (the API rejects them with `403`) |
| Actions (HR/Admin) | **+ New employee** · **Import** · **Export ▾** (CSV / XLSX) |
| Table (TanStack Table, server-side paging + sort) | Code · Name · Job role · Level · Department · Country · Type · Status · **Base salary** · **Total comp** (salary columns need `SALARY_READ`) · Hire date |
| Row | Click → detail. Terminated rows are greyed, with a "Terminated" badge |
| Footer | "Showing 26–50 of 9,700" · page size 25/50/100 · pagination |
| Empty | "No employees match these filters" + Clear filters |

Export uses the **current URL filters**: what you see is what you export ([11-import-export.md](11-import-export.md) §6).

### 4.5 Employee detail (`/employees/[id]`)

| Section | Content | Permission |
|---|---|---|
| Header | Name, code, status badge, job role · level · department · country · type, hire date; actions: **Edit**, **Terminate / Reactivate** (confirmation dialog), **Record salary change** | actions need `EMPLOYEE_WRITE` / `SALARY_WRITE` |
| **Current compensation** card | Base, each allowance, bonus target, **total comp**; Annual/Monthly toggle; USD equivalent with FX date; compa-ratio badge vs pay band (band min/mid/max shown on hover) | `SALARY_READ` |
| **Salary timeline** | Vertical timeline, newest first: date, reason badge (Hire / Promotion / Merit / Market adjustment / Correction), old → new base, **% change**, level/role change ("L2 → L3"), changed by. Small line chart of base over time | `SALARY_READ` |
| Activity (proposed) | Recent audit events for this employee | `AUDIT_READ` |

**Record salary change** (dialog / side sheet):
- Fields: effective date (default today; future dates not allowed, with an explanatory hint), reason (enum), new base, components editor (add/remove allowance rows; bonus target), optional new job role and level. **A Promotion must change the level or the job role**, and the form enforces this, mirroring the backend rule.
- A live preview shows "+8.5% vs current, new total comp €61,200 · ≈ US$66,100".
- Validation mirrors the backend (zod schemas built from the OpenAPI types).

**Edit employee**: profile fields only (name, email, employment type). **Salary, job role, level and country can't be edited here.** They change only through "Record salary change", so every change is captured in history with a reason. Department is derived from the job role and is not edited separately. The optimistic-lock `version` is sent in the request body.

### 4.6 Create employee (`/employees/new`)

Profile fields + initial compensation (base, components, currency defaulting from country). Creates the employee and the HIRE salary record in one request. On success, redirects to the detail page.

### 4.7 Import (`/employees/import`)

A three-step flow ([11-import-export.md](11-import-export.md)):

1. **Upload**: drag-and-drop or file picker (CSV/XLSX, ≤ 4 MB); "Download template (CSV | XLSX)"; short instructions ("Use 'CSV UTF-8' when saving from Excel").
2. **Review (dry-run)**:
   - Summary: rows, valid, errors; counts by country; total base by currency.
   - With errors: an errors table (row · column · problem · value, with "did you mean" suggestions), filterable by error type, plus a **"Download error report"** button. The commit button is disabled and the user is prompted to fix the file and re-upload.
   - With no errors: a preview table of the first 50 rows, and a "Ready to import 248 employees" call-to-action.
   - An expiry note: "This preview expires in 24 hours".
3. **Done**: "248 employees imported", with a link to the employee list filtered to the new codes **(proposed)**, or the failure message with nothing written ("No changes were made").

### 4.8 Ask about pay (`/ask`)

([10-ai-ask-design.md](10-ai-ask-design.md))

| Area | Content |
|---|---|
| Intro | "Ask about how ACME pays people. Answers use live data and show their sources." |
| Suggested questions (chips) | "Which country pays L3 engineers the most (USD)?" · "Are any teams paid below their band?" · "Average raise in 2025 by department?" · "Median total comp in Singapore?" |
| Conversation | Chat-style list. User bubble; **answer card** with markdown answer, **key figures** (amount + currency), caveats (e.g. "Full-time only · FX as of 2026-10-01"), **"How I got this"** (collapsible: tool names + arguments), **"View in dashboard"** link |
| Input | Text box (max 1,000 chars, same cap as the API) + Send; Enter sends, Shift+Enter adds a new line |
| Waiting | **Spinner** with "Thinking…" (no streaming in v1) |
| History | Kept in page state only; last 6 turns sent; "New conversation" clears it; a note says history is not saved |
| Errors | `429 rate-limited` → "The assistant is busy, try again in N s" (N from `Retry-After`; the problem `detail` says whether it's the hourly limit); `502 upstream-unavailable` → "The assistant is unavailable right now"; `503 feature-disabled` → the page isn't linked at all (`features.ask = false` from `/auth/me`) |
| Viewer | Same UI; access-limited answers are explained by the assistant |

### 4.9 Admin

> **Cut from v1** ([v1 scope](README.md#v1-scope-decided-2026-10-24-read-this-first)): no admin screens. Users, FX rates and countries are seeded. Kept here as the future-work design.

| Screen | Content |
|---|---|
| **Users** (`/admin/users`) | Table: name, email, role, active, last login (proposed). Actions: invite/create user (set a temporary password **(proposed)**), change role, deactivate. You can't deactivate or demote yourself (guard) |
| **FX rates** (`/admin/fx-rates`) | Table: currency, rate to USD, as-of, source. Edit a rate (decimal string input with validation), with a warning: "Changes affect all USD figures immediately; history is unaffected" |
| **Countries** (`/admin/countries`) | Code, name, default currency; edit the default currency (validated: must have an FX rate) |
| **Audit log** (`/admin/audit`) | Filterable table: time, actor, action, entity, summary; expandable diff JSON viewer; filters by actor, action, date range; URL-state |

---

## 5. Design workflow

> **v1:** no multi-step design phase. One time-boxed Claude Design canvas produced the chosen direction, "Marked-up printout": 6 desktop and 3 phone screens ([design/claude](design/claude/README.md)), with the rules in [design/DESIGN.md](design/DESIGN.md). The build uses shadcn/ui restyled to those rules; this doc wins on behaviour. Google Stitch was also tried (two directions) and dropped. The workflow below is the original, fuller plan.

([adr/0018-design-workflow.md](adr/0018-design-workflow.md), [16-claude-code-setup.md](16-claude-code-setup.md))

```mermaid
flowchart LR
    A[Screen contents<br/>this doc §4] --> B[Claude Design canvases<br/>5 key screens × 2 options]
    B --> C{User picks<br/>per screen}
    C --> D[docs/design/DESIGN.md<br/>tokens · type · spacing · components]
    D --> E[.claude/rules/design.md<br/>mirrored for Claude Code]
    D --> F[Build with shadcn/ui<br/>+ frontend-design skill]
    F --> G[Impeccable audit<br/>per screen, before PR merge]
    G -- findings --> F
    G --> H[Screenshots + audit notes<br/>docs/design/ + prompt log]
```

1. **Milestone 7b (design phase):** Claude Design / `/design` canvases for the **5 key screens**: Insights dashboard, Employee directory, Employee detail + salary timeline, Import review, Ask. Two options each; the user picks (or mixes).
2. **Freeze** the outcome as `docs/design/DESIGN.md`: colour tokens (light and dark), typography scale, spacing scale, radius, elevation, data-table rules, chart palette, iconography, component inventory (which shadcn components, which variants), and do/don't examples. Screenshots of the chosen canvases go in `docs/design/`.
3. **Mirror** the rules into `.claude/rules/design.md` (path-scoped to `frontend/**`) so Claude Code follows them while building.
4. **Build** with shadcn/ui + Tailwind v4 tokens from DESIGN.md, with the official **frontend-design** skill as guidance.
5. **Audit** each screen with **Impeccable** (anti-AI-slop rules; files reviewed before install) before its frontend PR merges. Findings and fixes are logged in [ai/prompt-log.md](ai/prompt-log.md). This is intentional evidence of catching and correcting AI output.

Google Stitch was considered and rejected: it adds a vendor, and its HTML output doesn't map to shadcn ([20-trade-offs.md](20-trade-offs.md)).

## 6. Visual direction (input to the design phase)

| Principle | Concretely |
|---|---|
| Calm, trustworthy, data-first | Neutral greys/slate base, **one accent colour**, semantic colours only for meaning (red = underpaid flag, amber = overpaid flag, green = success) |
| Numbers are the hero | Tabular numerals, right-aligned, a consistent decimals rule per currency, currency label always present |
| Dense but breathable tables | 40–44 px rows **(proposed)**, sticky header, zebra or hover highlight, truncation with tooltip |
| Typography | One clean sans family with true tabular figures; size scale ~12/14/16/20/24/32 **(proposed)** |
| Charts | Minimal gridlines, direct labels where possible, colour-blind-safe palette, every chart titled with its currency and population |
| Avoid "AI slop" | No purple gradients, no glassmorphism, no emoji headings, no cards inside cards, no generic hero sections. Impeccable enforces this |
| Themes | Light and dark, both meeting contrast requirements |

## 7. Accessibility (target: WCAG 2.2 AA)

- Colour contrast ≥ 4.5:1 for text and ≥ 3:1 for UI components and chart elements. Flags never rely on colour alone (an icon plus the text "Underpaid").
- Full **keyboard** operation: visible focus rings, logical tab order, `Esc` closes dialogs, focus trapped in modals and returned afterwards (Radix primitives via shadcn).
- Tables use proper `<th scope>`, sortable headers announce their sort state (`aria-sort`), and pagination has labelled buttons.
- Charts have an accessible text alternative: a "View as table" toggle under each chart **(proposed)**.
- Forms: labelled inputs, error messages linked via `aria-describedby`, errors announced on submit.
- Live regions announce toasts and "Thinking…" or answer-ready status on the Ask page.
- `eslint-plugin-jsx-a11y` in CI; **(proposed)** axe checks in Playwright smoke tests ([14-testing-strategy.md](14-testing-strategy.md)).
- Respects `prefers-reduced-motion` and `prefers-color-scheme`.

## 8. Responsive behaviour (fully mobile responsive)

**Every screen is fully usable on a phone**, not just "readable": every action available on desktop (search, filters, record a salary change, import, export, Ask, pay equity drill-down) works from 360 px wide upwards. Designs are made mobile-first and checked at **390 × 844** (phone), **768 × 1024** (tablet) and **1440 × 900** (desktop).

| Breakpoint (Tailwind) | Layout |
|---|---|
| < 640 px (`base`, phone) | Single column. Top bar collapses to the logo + a menu button that opens a navigation sheet. KPI tiles in a 2-column grid. Charts stack full width, using horizontal bars so labels stay readable |
| 640–1023 px (`sm`/`md`, tablet) | Two-column dashboard grid. Tables hide low-priority columns (hire date, type) behind a column picker |
| ≥ 1024 px (`lg`+, desktop) | Full dashboard grid; tables show all columns; side sheets open at the right |

Component rules on phones:

| Element | Phone behaviour |
|---|---|
| Data tables (employees, cohorts, top earners, import errors) | Become a **card list**: one card per row with the key fields (name, code, role · level, country, salary for HR) and a tap target to open the detail. No horizontal scrolling of the page |
| Filters | A "Filters (n)" button opens a bottom sheet with every filter; active filters show as removable chips under the search box |
| Toggles (Base/Total, Annual/Monthly) and population chip | Stay visible above the content as a compact segmented control |
| Side sheets and dialogs (record salary change, cohort drill-down, confirmations) | Open full screen with a sticky header (title + close) and a sticky footer (primary action) |
| Pay-equity range bars | Kept, scaled to the card width; numbers shown below the bar instead of beside it |
| Import | Upload by file picker (drag-and-drop is a desktop bonus); errors as cards grouped by row |
| Ask | Full-height chat; the input sticks to the bottom and stays above the on-screen keyboard |
| Pagination | "Previous / Next" with "26–50 of 9,700"; page-size picker hidden |

Rules that apply everywhere:
- Touch targets at least **44 × 44 px**; no hover-only information (tooltips also open on tap).
- No horizontal page scroll at any width ≥ 360 px; long names truncate with the full value on tap.
- Money stays on one line and never wraps between the symbol and the number; compact notation (`€1.2M`) is allowed in KPI tiles and charts on phones.
- Text inputs use the right mobile keyboard (`inputmode="decimal"` for amounts, `type="email"` for email, `type="search"` for search).
- Respects safe-area insets (`env(safe-area-inset-*)`) for the sticky header and footers.

## 9. Performance (UX budgets)

- API p95 < 300 ms for list and insight endpoints ([19-performance.md](19-performance.md)). UI target: interactive dashboard < 2.5 s LCP on a warm function.
- Search is debounced (300 ms). Filter changes use `startTransition` so the UI stays responsive.
- Charts are lazy-loaded below the fold.

## 10. Frontend testing hooks

([14-testing-strategy.md](14-testing-strategy.md))

- Vitest + RTL: `formatMoney`, URL-state parsing, role-gated rendering (VIEWER sees no salary column), forms (record-change validation), import review states.
- MSW mocks the typed API for component tests.
- Playwright smoke: login as Hema → search → record raise → see the insight change; login as Farah → no salary visible.

## 11. Open questions

- Top bar vs sidebar navigation: decided in the design phase (proposed: top bar).
- INR lakh grouping via the `en-IN` locale: **(proposed)**.
- "Link to newly imported employees" after an import: **(proposed)**.
- Role and level required on Promotion: **(proposed)**.
- Axe checks in Playwright: **(proposed)**.
