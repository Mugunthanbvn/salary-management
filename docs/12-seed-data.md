# 12 — Seed Data

> **Purpose:** Specify the deterministic seed that generates 10,000 realistic employees across 10 countries, with salary history, components, and a documented "demo story", plus how it is loaded locally and into Turso.

- **Status:** Draft for review
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [06-data-model.md](06-data-model.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [14-testing-strategy.md](14-testing-strategy.md) · [17-deployment.md](17-deployment.md) · [19-performance.md](19-performance.md) · [adr/0002-sqlite-everywhere-turso.md](adr/0002-sqlite-everywhere-turso.md) · [adr/0010-compensation-components.md](adr/0010-compensation-components.md)

---

## 1. Goals

| Goal | How |
|---|---|
| **Exactly 10,000 employees** (brief requirement) | `--employees 10000`, exact allocation by largest remainder |
| **Realistic enough that insights tell a story** | Country, level, and job-family pay bands; log-normal noise; components; raise history |
| **Exercises the hard cases** | Shared currency (EUR in DE + FR), zero-decimal currency (JPY), large numbers (INR), Unicode names, part-timers, terminated staff |
| **Deterministic** | Same `--seed` gives a byte-identical dataset, guarded by a checksum test |
| **Fast** | < 5 s locally for 10k employees + ~30k salary records + ~40k components ([19-performance.md](19-performance.md)) |
| **Honest** | All data is synthetic. The planted patterns are documented here and in `backend/src/salary_api/seed/README.md`, not hidden |

All values marked **(proposed)** are starting points to tune during milestone 6 ([18-implementation-plan.md](18-implementation-plan.md)). Final values are recorded in `seed_config.py`, a pure-data module, so tuning never touches generator logic.

---

## 2. Countries and currencies

Allocation uses **largest-remainder rounding**, so the counts are exact for any `--employees N`.

| Country | Code | Currency | Exponent | Share | Count (N = 10,000) | Edge case covered |
|---|---|---|---|---|---|---|
| United States | US | USD | 2 | 30% | 3,000 | Reporting currency |
| India | IN | INR | 2 | 25% | 2,500 | Large numbers (lakhs); HRA allowance |
| United Kingdom | GB | GBP | 2 | 10% | 1,000 | Transport allowance |
| Germany | DE | EUR | 2 | 8% | 800 | **EUR shared by two countries**; demo story |
| Canada | CA | CAD | 2 | 6% | 600 | |
| France | FR | EUR | 2 | 5% | 500 | **EUR shared**; meal allowance |
| Singapore | SG | SGD | 2 | 5% | 500 | Mixed-origin names |
| Australia | AU | AUD | 2 | 4% | 400 | |
| Japan | JP | JPY | **0** | 4% | 400 | **Zero-decimal currency**; non-Latin names |
| Brazil | BR | BRL | 2 | 3% | 300 | Accented names |

Each country's `default_currency` is stored in `countries` ([06-data-model.md](06-data-model.md)). All seeded employees are paid in their country's default currency.

## 3. Departments and job roles (controlled list)

Departments with share of headcount (allocated per country, largest remainder):

| Department | Share |
|---|---|
| Engineering | 35% |
| Sales | 15% |
| Operations | 10% |
| Customer Success | 10% |
| Marketing | 8% |
| Product | 6% |
| Finance | 6% |
| HR | 5% |
| Legal | 5% |

Job roles (`job_roles` table). Each has a **job family** used for the pay multiplier, and an allowed level range **(proposed)**:

| Department | Job role | Family | Levels | Family multiplier (proposed) |
|---|---|---|---|---|
| Engineering | Software Engineer | ENGINEERING | L1–L5 | 1.00 |
| Engineering | Frontend Engineer | ENGINEERING | L1–L5 | 1.00 |
| Engineering | Backend Engineer | ENGINEERING | L1–L5 | 1.00 |
| Engineering | Data Engineer | ENGINEERING | L1–L5 | 1.02 |
| Engineering | DevOps Engineer | ENGINEERING | L1–L5 | 1.00 |
| Engineering | QA Engineer | ENGINEERING | L1–L4 | 0.88 |
| Engineering | Engineering Manager | ENGINEERING | L4–L6 | 1.05 |
| Product | Product Manager | PRODUCT | L2–L6 | 1.00 |
| Product | Product Analyst | PRODUCT | L1–L4 | 0.85 |
| Product | Product Designer | DESIGN | L1–L5 | 0.92 |
| Product | UX Researcher | DESIGN | L1–L4 | 0.88 |
| Sales | Sales Development Representative | SALES | L1–L2 | 0.70 |
| Sales | Account Executive | SALES | L2–L5 | 0.90 |
| Sales | Sales Engineer | SALES | L2–L5 | 0.95 |
| Sales | Sales Manager | SALES | L4–L6 | 1.00 |
| Customer Success | Customer Success Manager | CUSTOMER_SUCCESS | L1–L5 | 0.78 |
| Customer Success | Support Specialist | CUSTOMER_SUCCESS | L1–L3 | 0.65 |
| Customer Success | Implementation Consultant | CUSTOMER_SUCCESS | L2–L4 | 0.85 |
| Marketing | Marketing Manager | MARKETING | L3–L6 | 0.92 |
| Marketing | Content Marketer | MARKETING | L1–L4 | 0.75 |
| Marketing | Growth Marketer | MARKETING | L1–L4 | 0.82 |
| Operations | Operations Analyst | OPERATIONS | L1–L4 | 0.75 |
| Operations | Project Manager | OPERATIONS | L2–L5 | 0.88 |
| Operations | IT Support Specialist | OPERATIONS | L1–L3 | 0.68 |
| Operations | Facilities Coordinator | OPERATIONS | L1–L3 | 0.60 |
| Finance | Financial Analyst | FINANCE | L1–L4 | 0.85 |
| Finance | Accountant | FINANCE | L1–L4 | 0.80 |
| Finance | Payroll Specialist | FINANCE | L1–L3 | 0.72 |
| Finance | Finance Manager | FINANCE | L4–L6 | 1.00 |
| HR | HR Business Partner | PEOPLE | L2–L5 | 0.85 |
| HR | Recruiter | PEOPLE | L1–L4 | 0.75 |
| HR | People Operations Specialist | PEOPLE | L1–L3 | 0.70 |
| Legal | Legal Counsel | LEGAL | L3–L6 | 1.10 |
| Legal | Paralegal | LEGAL | L1–L3 | 0.70 |
| Legal | Compliance Analyst | LEGAL | L1–L4 | 0.85 |

**35 roles.** Inside a department, roles are chosen with weights that favour the individual-contributor roles **(proposed)**, e.g. Software Engineer 35% of Engineering.

Why a controlled list: pay-equity cohorts are **job role + level + country** ([09-insights-pay-equity.md](09-insights-pay-equity.md)). Free-text titles ("Sr Engineer" vs "Senior Engineer") would fragment them. Forms and imports validate against this list ([11-import-export.md](11-import-export.md)).

## 4. Levels and employment type

| Level | Label | Share (pyramid) | Reference base USD, US, family 1.00 (proposed) | Bonus target |
|---|---|---|---|---|
| L1 | Associate | 25% | 70,000 | 5% |
| L2 | Mid | 30% | 95,000 | 8% |
| L3 | Senior | 25% | 125,000 | 10% |
| L4 | Lead / Staff | 12% | 155,000 | 15% |
| L5 | Principal | 6% | 190,000 | 20% |
| L6 | Director | 2% | 230,000 | 25% |

If the sampled level is outside a role's allowed range, it is **clamped** to the nearest allowed level. Clamping slightly distorts the pyramid; the final distribution is reported by the seed CLI.

Employment type: **~90% FULL_TIME, ~6% PART_TIME, ~4% CONTRACTOR.**

Status **(proposed)**: ~3% `TERMINATED`, with `termination_date` between hire_date and the seed anchor date. This exercises the default "active only" filter.

## 5. Base pay formula

```
reference_usd   = LEVEL_BAND_USD[level] × FAMILY_MULT[role.family] × COUNTRY_FACTOR[country]
noise           = exp( Normal(μ = 0, σ = 0.12) )                  # log-normal, ±~12%
base_usd        = reference_usd × noise
base_local      = base_usd / FX_RATE_TO_USD[currency]
base_local      = round_to(base_local, ROUNDING[currency])        # 1,000 local; 10,000 for INR and JPY
part-time       → base_local × Uniform(0.5, 0.8)  (then rounded)  # proposed: implied FTE not stored
```

Country factors (relative to the US in USD terms, **proposed**; tuned to look plausible, not market data):

| US | GB | DE | FR | CA | AU | SG | JP | IN | BR |
|---|---|---|---|---|---|---|---|---|---|
| 1.00 | 0.75 | 0.75 | 0.68 | 0.80 | 0.80 | 0.80 | 0.62 | 0.28 | 0.30 |

Worked example: **India, Software Engineer, L2**: 95,000 × 1.00 × 0.28 = 26,600 USD → ÷ 0.0120 = 2,216,667 INR → noise → rounded to the nearest 10,000, e.g. **₹22,20,000**.

All arithmetic is in `Decimal`, and the result is converted once to integer minor units ([adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md)).

## 6. Compensation components

Stored as `salary_components` rows on each salary record ([adr/0010-compensation-components.md](adr/0010-compensation-components.md)).

| Component | Type | Rule (proposed) | Applies to |
|---|---|---|---|
| HRA (House Rent Allowance) | ALLOWANCE | 40% of base | IN, FT + PT |
| Special Allowance | ALLOWANCE | 10% of base | IN, FT + PT |
| Meal Allowance | ALLOWANCE | €1,500 / year | FR, FT |
| Transport Allowance | ALLOWANCE | £1,200 / year (GB), €1,200 / year (DE) | GB, DE, FT |
| Bonus target | BONUS_TARGET | base × level % (§4); **Sales roles +5 percentage points** | FT + PT; **not contractors** |

Contractors get **no allowances and no bonus target (proposed)**.

`total_comp = base + Σ allowances + bonus target` is denormalized onto `employees.current_total_minor` ([09-insights-pay-equity.md](09-insights-pay-equity.md) §2.2).

## 7. Salary history

Each employee gets **1 to ~6 salary records** (append-only; [adr/0006-append-only-salary-history.md](adr/0006-append-only-salary-history.md)), **~30k in total**. Each record carries a `job_role_id` + `level` **snapshot**, so history can show "L2 → L3, Promotion, +12%".

**Back-casting (proposed)** keeps current pay on the bands. The current base is generated first (§5), then history is walked **backwards** from today:

1. **Hire date:** tenure ~ Exponential(mean 3.5 years), capped at 11 years, and never later than the seed anchor date. Hire dates fall between 2015-10 and 2026-09.
2. **Anniversaries:** on each work anniversary before the anchor date:
   - with probability **0.55** there is a **MERIT** raise of Uniform(2%, 6%);
   - once per employee, with probability **~15%** overall, a **PROMOTION** of Uniform(10%, 15%) and level − 1 going back in time (only if the earlier level is still in the role's allowed range).
3. A small number **(proposed: 1%)** of **MARKET_ADJUSTMENT** (+5–10%) records, and **0.5%** **CORRECTION** records (−3% to +3%).
4. Walking back divides the base by each raise factor. The earliest record is the **HIRE** record at `hire_date`.
5. Amounts are re-rounded at each step to the currency's rounding unit. Components are recomputed per record from the rules in §6, using that record's level.
6. `changed_by` = the seed system user; reasons use the enum `HIRE`, `PROMOTION`, `MERIT`, `MARKET_ADJUSTMENT`, `CORRECTION`.

This guarantees the current distribution matches §5. The raises insight ([09-insights-pay-equity.md](09-insights-pay-equity.md) §3.7) gets a realistic spread.

## 8. Demo story (planted, documented patterns)

The data is planted so pay equity and "Ask about pay" have **real findings** to show in the demo video ([10-ai-ask-design.md](10-ai-ask-design.md)):

| Pattern | Mechanics | Where it shows up |
|---|---|---|
| **~2% individual outliers** | 2% of FT active employees (chosen by RNG): 60% get their current base × Uniform(0.65, 0.75) (**underpaid**), 40% × Uniform(1.30, 1.45) (**overpaid**). Applied to the generated current base **before** back-casting, so the whole history scales consistently | Pay-equity outlier flags (compa-ratio < 0.8 or > 1.2) |
| **Customer Success in Germany ~8% under band** | Every DE employee in a Customer Success role: current base × 0.92 | Pay-equity department rollup (median compa-ratio vs band ≈ 0.92); Ask: "Are we underpaying anyone in Germany?" |

> **Detectability (decided).** Compa-ratio is measured against the **pay band midpoint**, not the cohort's own median ([09-insights-pay-equity.md](09-insights-pay-equity.md) §3.8). Bands are seeded from the **pre-noise reference formula** in §5 (`mid` = reference × factors → local currency; `min` = 0.8 × mid; `max` = 1.2 × mid), so they are independent of the generated salaries. The team-wide −8% in DE Customer Success therefore shows as a department median compa-ratio ≈ 0.92 (below the 0.95 threshold), while normal departments sit ≈ 1.00 (log-normal noise has median 1). Individual outliers (×0.65–0.75 / ×1.30–1.45) fall outside 0.8–1.2 and are flagged.

**Pay bands seeded:** one row in `pay_bands` per job role × level × country (about 30 × 6 × 10 = 1,800 rows), `effective_from` = 2026-01-01 **(proposed)**. A test asserts every active employee has a band.

Both patterns can be switched off (`--no-story`) for tests that need a "clean" distribution.

## 9. Names and emails

Generated with **Faker**, one locale per country:

| Country | Faker locale | Notes |
|---|---|---|
| US | `en_US` | |
| IN | `en_IN` | |
| GB | `en_GB` | |
| DE | `de_DE` | `Müller`, `Jürgen`: tests Unicode search |
| FR | `fr_FR` | `Élodie`, `François` |
| CA | `en_CA` | |
| SG | **Curated name lists** in `seed_config.py` (decided): about 40 first and 30 last names across Chinese (romanized: Tan, Lim, Ng, Wei Ling…), Malay (Nur Aisyah, Muhammad Hafiz…) and Indian (Priya, Ramasamy…) origins, sampled with the seeded RNG | Faker has no `en_SG`, and mixing other locales gives unrealistic names. A small fixed list is deterministic and realistic |
| AU | `en_AU` | |
| JP | `ja_JP` | Display name in kanji (e.g. 佐藤 花子); email from `romanized` names |
| BR | `pt_BR` | `José`, `Conceição` |

- `employee_code`: sequential `ACME-000001` … `ACME-010000`.
- `email`: `first.last.<last 4 digits of code>@acme.example`, ASCII-folded (NFKD + strip accents; romanized for JP). `.example` is a **reserved domain** (RFC 2606), so no real person is ever emailed.
- `search_text` = lowercased **and accent-stripped** (NFKD) `"first last code email"`, so `muller` finds `Müller`. Used for case- and accent-insensitive search ([06-data-model.md](06-data-model.md)).

## 10. FX snapshot (illustrative)

Seeded into `fx_rates` with `as_of = 2026-10-01` and `source = "illustrative static snapshot"`. These rates are **for demo purposes only**, not live market data. Admins can edit them (`FX_ADMIN`).

| Currency | rate_to_usd (1 unit = X USD) |
|---|---|
| USD | 1.0000 |
| EUR | 1.0800 |
| GBP | 1.2700 |
| INR | 0.0120 |
| JPY | 0.0067 |
| CAD | 0.7300 |
| SGD | 0.7400 |
| AUD | 0.6600 |
| BRL | 0.1800 |

Stored as decimal strings ([adr/0005-fx-read-time-conversion.md](adr/0005-fx-read-time-conversion.md)).

## 11. Users

| Email | Persona | Role | Password source |
|---|---|---|---|
| `admin@acme.example` | Arun | ADMIN | `SEED_ADMIN_PASSWORD` |
| `hr@acme.example` | Hema | HR_MANAGER | `SEED_HR_PASSWORD` |
| `viewer@acme.example` | Farah | VIEWER | `SEED_VIEWER_PASSWORD` |

- With `APP_ENV=development`, documented dev defaults are allowed for convenience.
- With `APP_ENV=production`, the app **refuses to start** with default or missing secrets, and the seed refuses default passwords.
- The **deployed demo's** credentials are shared in the README and the submission email (synthetic data only), so reviewers can log in as each role and see Viewer masking ([08-security-rbac.md](08-security-rbac.md)).

## 12. Determinism

| Mechanism | Detail |
|---|---|
| Single RNG | `rng = random.Random(seed)` passed explicitly to every generator function; no global `random` |
| Faker | One `Faker(locale)` instance per country, each `seed_instance(seed + country_index)` |
| Fixed anchor date | `SEED_ANCHOR_DATE = 2026-10-01` (config). All dates are relative to it, **not** to `today()`, so re-running next month gives identical data |
| Stable iteration | Countries, departments, and roles are iterated in config order (lists, not sets) |
| Exact allocation | Largest-remainder rounding for countries, departments, levels, and types |
| No wall-clock or UUID randomness | IDs are integers assigned in generation order |

**Checksum test** ([14-testing-strategy.md](14-testing-strategy.md)):

- Generate with `--seed 42 --employees 10000` into in-memory SQLite.
- Assert exact counts per country (table in §2) and per department.
- Assert `sha256` over the sorted tuples `(employee_code, country, job_role, level, employment_type, current_base_minor, current_total_minor)` equals a **golden value** committed in the test.
- Assert invariants: every employee has ≥ 1 salary record, the latest record matches the denormalized current salary, no amount ≤ 0, JPY amounts are whole yen, every currency has an FX rate.
- A fast variant with `--employees 200` runs in the default unit suite. The full 10k check runs in CI's integration job.

If the generator logic changes on purpose, the golden checksum is updated **in the same commit**, with the reason in the commit message.

## 13. Loading

### 13.1 Local / tests

- Schema via Alembic (`alembic upgrade head`), then the generator inserts with **SQLAlchemy Core `insert()` executemany in chunks of 1,000**, inside one transaction per table batch.
- SQLite pragmas during seeding: `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`.
- Target: **< 5 s** for 10k employees on a laptop (measured and recorded in [19-performance.md](19-performance.md)).

### 13.2 Turso (production)

Inserting ~80k rows one network round-trip at a time into a remote DB is slow. The seed therefore builds a local file and uploads it:

1. `make seed-file` → runs migrations + seed into `./build/acme-seed.db` (with a WAL checkpoint, so it is a single self-contained file).
2. `turso db create acme-salary --from-file ./build/acme-seed.db` (first time), **or** for a re-seed: destroy and re-create (demo data only; documented).
3. Verify: row counts via `turso db shell acme-salary "select count(*) from employees"` and the `/api/health` endpoint.
4. Alembic's version table travels with the file, so later migrations apply normally.

Exact Turso CLI flags and file-size limits are **verified during the milestone 1 deploy spike** ([17-deployment.md](17-deployment.md)). The fallback (Neon Postgres) seeds via the normal insert path against the pooled URL.

## 14. CLI

```bash
# local dev (default DATABASE_URL = sqlite:///./salary.db)
make seed                                   # = uv run python -m salary_api.seed --seed 42 --employees 10000 --reset

# explicit
uv run python -m salary_api.seed \
  --seed 42 \
  --employees 10000 \
  --reset \                 # drop + recreate data (refuses on APP_ENV=production unless --force-demo)
  --no-story \              # disable demo-story distortions
  --no-history \            # one HIRE record per employee (fast tests)
  --db-url sqlite:///./build/acme-seed.db

# build the Turso upload file
make seed-file
```

Output: a summary table (counts per country, department, level, and type; salary records; components; duration).

## 15. Open questions

- All numeric parameters marked **(proposed)**: tune in milestone 6.
- ~~Singapore name locales~~ **Decided:** curated name lists (§9).
- How the DE Customer Success pattern is surfaced: **TBD** (milestone 7).
- Terminated share ~3% **(proposed)**.
