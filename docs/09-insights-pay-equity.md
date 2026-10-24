# 09 — Insights & Pay Equity

> **Purpose:** Define every insight the product offers: the question each one answers, its inputs, the exact formula, and the output shape. This is the reference that the dashboard, the API, the tests, and the AI "Ask about pay" feature all build on.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [06-data-model.md](06-data-model.md) · [07-api-spec.md](07-api-spec.md) · [08-security-rbac.md](08-security-rbac.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [13-frontend-ux.md](13-frontend-ux.md) · [19-performance.md](19-performance.md) · [adr/0005-fx-read-time-conversion.md](adr/0005-fx-read-time-conversion.md) · [adr/0007-pure-python-stats.md](adr/0007-pure-python-stats.md) · [adr/0009-permission-rbac-small-group-rule.md](adr/0009-permission-rbac-small-group-rule.md) · [adr/0010-compensation-components.md](adr/0010-compensation-components.md)

---

## 1. Why this document exists

The problem statement asks that the HR manager be able to "**answer questions about how the org pays people**". With salaries in many currencies, the same pay data can give misleading answers when it is aggregated naively. For example, an average that mixes INR and USD amounts is meaningless.

This document pins down:

1. **Which questions** the product answers.
2. **Exactly how** each number is computed: formulas, percentile method, rounding.
3. **Which currency** every number is expressed in, and when conversion happens.
4. **Who can see what**: masking and the small-group rule.
5. **Edge cases**: empty groups, mixed currencies, part-time staff.

Each insight below is implemented once, in the `insights` service. The dashboard, CSV/XLSX export, and the AI tools all call that service, so they cannot disagree.

---

## 2. Global rules (apply to every insight)

### 2.1 Population defaults

| Rule | Default | Override |
|---|---|---|
| Employment status | `ACTIVE` only. Terminated employees are excluded from pay insights | `status` filter (admin and HR can include terminated for historical views) |
| Employment type | **`FULL_TIME` only**. Part-time pay is not full-time-equivalent and would pull averages and medians down; contractors are paid on different terms | `employment_type` filter (multi-select) |
| As-of date | "Current" means each employee's latest `salary_record` (effective_date ≤ today), held denormalized on `employees` | None in v1 (point-in-time insights are out of scope; see [01-prd.md](01-prd.md)) |

The UI shows the active population filter as a visible chip ("Full-time, active employees"), so the default is never hidden. See [13-frontend-ux.md](13-frontend-ux.md).

### 2.2 Compensation basis: `comp=base|total`

Every insight takes `comp`:

| `comp` | Definition |
|---|---|
| `base` (default) | Annual base salary from the current salary record (`base_minor`) |
| `total` | **Total compensation = base + Σ allowances + bonus target**, where the bonus target is stored as an amount in `salary_components` (type `BONUS_TARGET`). Equity, commission, overtime, and benefits are not modelled (see [adr/0010-compensation-components.md](adr/0010-compensation-components.md)) |

`total` is denormalized as `employees.current_total_minor` and written in the same transaction as the salary record. Insight queries therefore never re-sum components at read time.

### 2.3 Period: `annual` vs `monthly`

- Stored values are **annual**.
- Monthly is a **display transformation only** (annual ÷ 12), done client-side in the formatting layer (see [13-frontend-ux.md](13-frontend-ux.md)). The API always returns annual values, so there is one source of truth.
- Rounding for monthly display: half-even at the currency's minor unit, display only. Monthly values are never stored or summed.

### 2.4 Money representation

- All amounts are **integer minor units** plus an **ISO 4217 currency code** (see [adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md)).
- The minor-unit exponent comes from currency metadata (JPY = 0, USD/EUR/GBP/INR/… = 2).
- Arithmetic in the domain layer uses Python `int` (sums, means) and `decimal.Decimal` (percentiles, ratios, FX). **Floats are never used for money.**
- API responses carry amounts as `{ "amount_minor": 5200000, "currency": "EUR" }`. Rendering (thousands separators, symbols) is the client's job.

### 2.5 Currency-context rules (the core anti-misleading rule)

| Situation | Rule |
|---|---|
| Statistic over a group where **all members share one currency** (e.g. one country, or DE+FR together in EUR) | Computed and returned **in that local currency**. Optionally also returned in USD (`usd_equivalent`) |
| Statistic over a group that **mixes currencies** (e.g. "whole org", "Engineering across all countries") | Computed **only in USD**, by converting each individual amount to USD *before* aggregation (§2.6). Never sums or averages local amounts across currencies |
| Salary-range filter (`salary_min`/`salary_max`) | **Requires `SALARY_READ`** (Viewers get `403`, because filtering by salary could reveal individual pay). Requires `currency` to be set (range applies to amounts in that currency), **or** `salary_basis=usd` (range applies to USD-converted amounts). Otherwise the API returns `422` with a clear message |
| Comparing two countries | Done in USD, and the response states the FX `as_of` date |

Every response that contains a USD figure also contains `fx_as_of` (the oldest `as_of` among the rates used). The UI shows it next to the figure, with the source in a tooltip.

### 2.6 USD conversion

- `fx_rates` stores `rate_to_usd` per currency as a **decimal string** (e.g. `"0.01198"` for INR), plus `as_of` and `source` (see [06-data-model.md](06-data-model.md)).
- Conversion of one amount:

  ```
  usd_minor = round_half_even( amount_minor × 10^(2 − exp(ccy)) × rate_to_usd )
  ```

  Here `exp(ccy)` is the source currency's minor-unit exponent and 2 is the USD exponent. All arithmetic is in `Decimal`.
- Conversion happens **at read time only**. Converted values are never stored ([adr/0005-fx-read-time-conversion.md](adr/0005-fx-read-time-conversion.md)).
- For mixed-currency groups, each amount is converted individually, then aggregated. Aggregating locally and then converting would give the same mean but a **wrong median and percentiles** across currencies.

### 2.7 Statistics definitions

These are implemented as **pure functions** in `domain/stats.py`, unit-tested without a database ([adr/0007-pure-python-stats.md](adr/0007-pure-python-stats.md)). SQL only fetches the relevant amounts, sorted, per group.

| Statistic | Definition |
|---|---|
| `count` | Number of employees in the group after filters |
| `min`, `max` | Smallest and largest amount |
| `sum` | Σ amounts (integer; same currency only, or USD) |
| `mean` | `sum / count`, rounded **half-even** to the minor unit, in exact integer arithmetic (`domain/rounding.py`; never float) |
| `median` | `percentile(0.5)` |
| `p25`, `p75` | `percentile(0.25)`, `percentile(0.75)` |
| `percentile(p)` | **Linear interpolation between closest ranks**, the same as NumPy's default (`method="linear"`) and SQL `PERCENTILE_CONT`. For sorted values `x[0..n-1]`: `h = (n − 1) × p`, `lo = floor(h)`, `hi = ceil(h)`, `result = x[lo] + (h − lo) × (x[hi] − x[lo])`, computed in `Decimal` and rounded half-even to the minor unit |
| `iqr` | `p75 − p25` (used for distribution context) |

Why this method: it is the most common definition in analytics tools, it matches Postgres `percentile_cont`, and it keeps the [scaling path](19-performance.md) (moving percentiles into SQL) behaviour-preserving. Golden tests compare our function to hand-computed values and to NumPy on fixed arrays (see [14-testing-strategy.md](14-testing-strategy.md)).

### 2.8 Small-group rule (privacy)

- If a group has **fewer than 5 people** (`n < 5`), its aggregates would reveal individual salaries. For a group of 1, the "average" *is* that person's pay.
- For users **without `SALARY_READ`** (the `VIEWER` role), any group with `count < 5` returns `suppressed: true`. All monetary fields **and `count`** are `null`. The group key is still listed, so the user knows the group exists, and the UI shows "—" with the tooltip "Hidden to protect individual pay (fewer than 5 people)". The count is hidden too: combined with other figures (e.g. department totals), a small count could help re-identify individuals.
- Users with `SALARY_READ` (HR_MANAGER, ADMIN) can see individual salaries anyway, so suppression does not apply to them.
- The threshold `MIN_GROUP_SIZE = 5` is a single named constant (setting), tested at the boundary (n = 4 suppressed, n = 5 shown).
- The rule is enforced **in the service layer**, so the dashboard, exports, and the AI tools all inherit it. See [08-security-rbac.md](08-security-rbac.md).

### 2.9 Common output shape

Every insight response carries `population` (the filters actually applied) and `fx_as_of` whenever USD appears. Each group holds a **stats object** as defined in [07-api-spec.md](07-api-spec.md) §8.2: `{ count, min, p25, median, mean, p75, max, currency, suppressed }`, with integers in minor units of `currency`.

```json
{
  "population": { "country": ["DE"], "employment_type": ["FULL_TIME"], "status": ["ACTIVE"], "comp": "base" },
  "currency": "EUR",
  "fx_as_of": "2026-10-01",
  "groups": [
    {
      "department": { "id": 1, "name": "Engineering" },
      "stats": { "count": 412, "min": 4200000, "p25": 4900000, "median": 5400000, "mean": 5523000, "p75": 6300000, "max": 14500000, "currency": "EUR", "suppressed": false }
    }
  ]
}
```

For a mixed-currency population the response `currency` is `USD`. Exact schemas live in the OpenAPI contract (see [07-api-spec.md](07-api-spec.md), the [glossary](glossary.md) and [adr/0014-contract-first-openapi-client.md](adr/0014-contract-first-openapi-client.md)).

---

## 3. Insight catalogue

Every insight requires the `INSIGHTS_READ` permission unless stated otherwise. All accept the common filters: `country`, `department`, `job_role`, `level`, `employment_type`, `status`, and `comp`.

### 3.1 Org overview: `GET /api/v1/insights/overview`

**Answers:** "How big is the org, what do we spend on pay, and how does pay look in each country?"

| Output | Formula | Currency |
|---|---|---|
| Headcount | `count` of the population | — |
| Total annual payroll | Σ of each employee's amount converted to USD | USD |
| By-country table | Per country: count, min, p25, median, mean, p75, max | Local currency **plus** USD equivalent of each statistic |
| Headcount by country / department | `count` per key | — |

Notes: DE and FR both use EUR, but they are still separate rows, because country is the grouping key, not currency.

### 3.2 Pay by department: `GET /api/v1/insights/by-department`

**Answers:** "What is the average and median salary in each department?"

- Grouped by department.
- If a `country` filter is set (single currency), statistics are in **local currency**.
- Without a country filter, the groups mix currencies, so statistics are in **USD** (response `currency: "USD"`, plus `fx_as_of`) and the UI says so.

### 3.3 Pay by job title within a country: `GET /api/v1/insights/by-job-title`

**Answers:** "Within India, what do Software Engineers vs Data Engineers earn?"

- **`country` is required.** Job-title pay only means something within one market and currency. Missing `country` returns `422`.
- Grouped by `job_role` (and optionally by `level` with `split_by_level=true`).
- Local currency.

### 3.4 Salary distribution: `GET /api/v1/insights/distribution`

> **Cut from v1** ([v1 scope](README.md#v1-scope-decided-2026-10-24-read-this-first)). Kept here as the future-work design.

**Answers:** "How is pay spread? Is it bunched or long-tailed?"

- Single-currency populations (`country` set, or the `currency` filter): bins in local currency.
- Mixed populations: bins in USD.
- **Binning (proposed):** 20 equal-width bins between the population's p1 and p99. Values below p1 and above p99 go into open-ended edge bins ("< x", "> y"), so a few outliers don't squash the chart.
- Output: `bins: [{ "from": {...}, "to": {...}, "count": 123 }]` plus summary statistics (median, p25, p75) for reference lines on the chart.
- Small-group rule: a bin's *count* is not salary-revealing on its own, but for Viewers any bin with `count < 5` has its count returned as `null` (`suppressed: true`), consistent with §2.8. A bin plus a filter narrow enough could otherwise reveal an individual's band.

### 3.5 Department cost: `GET /api/v1/insights/department-cost`

**Answers:** "How much do we spend on salaries per department?"

- Σ of each employee's amount converted to USD, per department (optionally per country).
- Output also includes `share_of_total` (Decimal, 4 dp) and `headcount`.
- Always USD unless a single-country filter is applied, in which case the local currency is returned with a USD equivalent.

### 3.6 Top / bottom earners: `GET /api/v1/insights/top-earners`

**Answers:** "Who are the highest- and lowest-paid people in the UK?"

- **Requires `SALARY_READ`** (HR_MANAGER, ADMIN). It returns individuals. Viewers get `403`.
- **`country` is required** (local-currency ranking). Parameters: `n` (default 10, max 50), `direction=top|bottom`.
- Ties are broken by `employee_code` ascending, so results are deterministic.
- Output: list of `{ employee_code, name, job_role, level, department, amount }`.
- Writes an `insights.individuals_view` audit event because it exposes individual pay (see [08-security-rbac.md](08-security-rbac.md)).

### 3.7 Raises: `GET /api/v1/insights/raises`

> **Cut from v1** ([v1 scope](README.md#v1-scope-decided-2026-10-24-read-this-first)). Kept here as the future-work design. Open issue for later: a `CORRECTION` record can't neutralise a wrong earlier raise in these statistics; a `corrects_record_id` link would fix that.

**Answers:** "What raises did we give last year, by department and reason?"

- Input: `from`, `to` (effective_date range, required), optional `group_by=department|country|reason`.
- For each `salary_record` with `effective_date` in range and reason ≠ `HIRE`, compare it with the **previous** record of the same employee:
  - `raise_pct = (new_base − prev_base) / prev_base`, in `Decimal`, 4 dp.
  - The comparison is always within the same currency. If the currency changed between records (rare; e.g. relocation), the raise is excluded and counted in `excluded_currency_change`.
- Output per group: `count`, `mean_raise_pct`, `median_raise_pct`, `count_by_reason` (`PROMOTION`, `MERIT`, `MARKET_ADJUSTMENT`, `CORRECTION`).
- Uses base salary only. A component change doesn't count as a "raise" in v1 (documented limitation).

### 3.8 Pay equity: `GET /api/v1/insights/pay-equity`

**Answers:** "Are we paying people fairly against the pay band for their job? Who looks underpaid or overpaid? Is any *team* systematically paid below band?"

#### Why bands, not the peer-cohort median
An earlier draft defined compa-ratio as salary ÷ median of the peer cohort. That **can't detect systemic underpayment**: if an entire cohort is paid 8% less, its median drops by 8% too, and everyone still looks "in band". HR practice defines compa-ratio against an **external benchmark, the pay band midpoint**. That's what we use. The cohort spread (P25/median/P75) is still reported, as context next to the band. Decision recorded in the [docs README](README.md) decision log (#1), [ADR 0007](adr/0007-pure-python-stats.md) and [06-data-model.md](06-data-model.md) (`pay_bands`).

#### Pay bands
- A **pay band** exists per **job role + level + country** (same country means the same currency and labour market). Columns: `min`, `mid`, `max` (minor units, local currency) and `effective_from`.
- Bands are **seeded** from the same reference formula the seed uses to generate salaries, **before noise** ([12-seed-data.md](12-seed-data.md)):
  - `mid` = USD reference band × country factor × level multiplier × family multiplier → local currency, rounded like salaries;
  - `min` = 0.80 × mid;
  - `max` = 1.20 × mid.

  A ±20% band width is typical for salaried roles.
- v1 bands are **read-only** in the UI (visible on the pay-equity screen and the employee detail page). Editing bands is future work. Changes would be audited and need `REFERENCE_ADMIN`.

#### Compa-ratio

```
compa_ratio(employee) = employee_base / band(job_role, level, country).mid
```

- Uses **base salary only**. Bands are defined on base pay, and allowances follow country policy (for example India's HRA), not the role's market value. The `comp` toggle doesn't apply to this endpoint, and the UI disables it there with a tooltip.
- Computed in `Decimal`. Shown rounded to 2 dp; full precision is kept for flag decisions.
- An employee whose role + level + country has **no band** gets `compa_ratio: null` and `no_band: true`, is excluded from the rollups, and is counted in `summary.employees_without_band` (expected to be 0 with seeded data; a test asserts this).
- A **non-`FULL_TIME`** employee (part-time or contractor) also gets `compa_ratio: null` and is excluded from the rollups: their pay isn't FTE-normalised, so comparing it with a full-time band would mislead. This check comes before the band check (`domain/pay_equity.py`, reason `not_full_time`).

#### Flags

| Compa-ratio | Flag | Meaning |
|---|---|---|
| `< 0.80` (exactly 0.80 is in band) | `UNDERPAID` | Below band minimum: possible fairness or retention risk |
| `0.80 – 1.20` | `IN_BAND` | Within band |
| `> 1.20` | `OVERPAID` | Above band maximum: cost or band-drift risk |

Because `min = 0.8 × mid` and `max = 1.2 × mid`, the flags mean "below band minimum" and "above band maximum". Thresholds are named settings (`PAY_EQUITY_LOW = 0.80`, `PAY_EQUITY_HIGH = 1.20`), tested at both boundaries.

#### Views

**1. Department rollup (the systemic-gap view).** `?view=departments&country=DE`
Per **department × country**: `count`, `mean_compa_ratio`, `median_compa_ratio`, `pct_below_band`, `underpaid_count`, `overpaid_count`.
This is how the seeded story surfaces: Customer Success in DE shows a median compa-ratio of about **0.92**, while other DE departments sit near 1.00 ([12-seed-data.md](12-seed-data.md) §8). The UI highlights any department whose median compa-ratio is below **0.95** **(proposed)** as "systematically below band".

**2. Cohort summary.** `?view=cohorts` (default)
Per **job role + level + country**: `count`, base P25/median/P75, band `min/mid/max`, `median_compa_ratio`, `underpaid_count`, `overpaid_count`.

**3. Employee drill-down.** `GET /api/v1/insights/pay-equity/cohort?country=DE&job_role_id=...&level=L2`
**Requires `SALARY_READ`.** Returns flagged employees with `employee_code`, name, base, band, compa-ratio and flag.

Visibility: summaries and rollups need `INSIGHTS_READ`. For a Viewer, any group with `count < 5` has its counts, ratios and monetary fields set to `null` with `suppressed: true` (small-group rule, §2.8). Band values are treated as aggregates: they aren't individual pay, so they stay visible.

> **Individual salary masking (related convention):** wherever an API response would contain an individual's salary and the caller lacks `SALARY_READ`, the amount fields are `null` and the object carries `"salary_masked": true` ([07-api-spec.md](07-api-spec.md), [08-security-rbac.md](08-security-rbac.md)). Small-group suppression (`suppressed: true`) is the aggregate counterpart.

#### Output (department rollup)

```json
{
  "view": "departments",
  "country": "DE",
  "currency": "EUR",
  "groups": [
    { "key": { "department": "Customer Success" }, "count": 41, "median_compa_ratio": "0.92", "mean_compa_ratio": "0.93", "pct_below_band": "0.29", "underpaid_count": 12, "overpaid_count": 0, "suppressed": false, "below_threshold": true },
    { "key": { "department": "Engineering" }, "count": 287, "median_compa_ratio": "1.00", "mean_compa_ratio": "1.01", "pct_below_band": "0.04", "underpaid_count": 11, "overpaid_count": 9, "suppressed": false, "below_threshold": false }
  ],
  "summary": { "employees_evaluated": 800, "employees_without_band": 0, "employees_flagged_underpaid": 41, "employees_flagged_overpaid": 17 }
}
```
*(Numbers illustrative.)*

#### Output (cohort summary)

```json
{
  "view": "cohorts",
  "cohorts": [
    {
      "key": { "country": "DE", "job_role": "Customer Success Manager", "level": "L2" },
      "count": 18,
      "currency": "EUR",
      "p25": {...}, "median": {...}, "p75": {...},
      "band": { "min": {...}, "mid": {...}, "max": {...} },
      "median_compa_ratio": "0.91",
      "underpaid_count": 5,
      "overpaid_count": 0,
      "suppressed": false
    }
  ],
  "summary": { "cohorts_evaluated": 412, "employees_without_band": 0, "employees_flagged_underpaid": 168, "employees_flagged_overpaid": 61 }
}
```

---

## 4. Edge cases

| Case | Behaviour |
|---|---|
| Filters match **no employees** | `200` with `groups: []` (or `count: 0`). Monetary fields are `null`. The UI shows an empty state, not an error |
| Group with `count < 5` | Viewer: `suppressed: true`. HR/Admin: shown normally. Pay-equity still computes compa-ratio for every employee with a band (no minimum peer count needed) |
| Percentile of a single value | Equals that value (the formula handles `n = 1`) |
| Mixed currencies with no USD rate for one currency | `500`-class configuration error, logged and surfaced as a problem+json `fx_rate_missing`. Seeded and admin-managed rates prevent this, and a test asserts every currency in `countries` has a rate |
| Salary range filter without `currency` or `salary_basis=usd` | `422` with the message "Salary range needs a currency or USD basis" |
| `by-job-title` / `top-earners` without `country` | `422` (single-market requirement) |
| Employee whose currency differs from the country default | Can't happen in v1: every salary is in its country's currency (validated on write, [06-data-model.md](06-data-model.md) §4.2). So a country group is always single-currency, and compa-ratio always divides amounts in the same currency |
| JPY (0 decimals) | Handled by the exponent table. Means and percentiles round to whole yen |
| Very large INR values | Integers have no precision issue (BIGINT; Python `int` is unbounded) |
| Terminated employees | Excluded by default; included only via the explicit `status` filter |
| Part-time / contractor | Excluded by default. When included, the UI warns "Includes part-time / contractor pay (not FTE-normalised)" |

---

## 5. Consistency guarantees

- **One implementation:** dashboard endpoints, exports, and AI tools ([10-ai-ask-design.md](10-ai-ask-design.md)) call the same `InsightService` methods.
- **Same results on SQLite and Postgres:** statistics are computed in Python, and SQL only selects and sorts. The Postgres CI job runs the same insight tests ([14-testing-strategy.md](14-testing-strategy.md)).
- **Deterministic:** ordering ties are broken by `employee_code`; Decimal rounding is half-even everywhere.

## 6. Performance notes

The largest query is 10k amounts per request. Fetching sorted integers and computing in Python takes single-digit milliseconds. The indexes in [06-data-model.md](06-data-model.md) §4.5 (`country_code, status`; `job_role_id, level`; `status, employment_type`) support the filters; department filters join through `job_roles`. Budgets and the scaling path are in [19-performance.md](19-performance.md).

## 7. Open questions

- ~~Reference-band rollup in v1?~~ **Decided:** yes. Band-based compa-ratio + department rollup (§3.8).
- ~~Should `top-earners` access write an audit event?~~ **Decided:** yes, `insights.individuals_view`.
- Distribution binning: 20 bins between p1 and p99 **(proposed)**.
