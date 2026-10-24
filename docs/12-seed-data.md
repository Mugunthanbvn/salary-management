# 12 — Seed Data

> **Purpose:** Specify the deterministic seed that generates 10,000 realistic employees across 10 countries, with salary history, components, and a documented "demo story", plus how it is loaded locally and into Turso.

- **Status:** Built (B5). Values marked **(proposed)** are the ones in `seed_config.py`
- **Last updated:** 2026-10-24
- **Related docs:** [01-prd.md](01-prd.md) · [06-data-model.md](06-data-model.md) · [09-insights-pay-equity.md](09-insights-pay-equity.md) · [10-ai-ask-design.md](10-ai-ask-design.md) · [14-testing-strategy.md](14-testing-strategy.md) · [17-deployment.md](17-deployment.md) · [19-performance.md](19-performance.md) · [adr/0002-sqlite-everywhere-turso.md](adr/0002-sqlite-everywhere-turso.md) · [adr/0010-compensation-components.md](adr/0010-compensation-components.md)

---

## 1. Goals

| Goal | How |
|---|---|
| **Exactly 10,000 employees** (brief requirement) | `--employees 10000`, exact allocation by largest remainder |
| **Realistic enough that insights tell a story** | Country, level, and job-family pay bands; log-normal noise; components; raise history |
| **Exercises the hard cases** | Shared currency (EUR in DE + FR), zero-decimal currency (JPY), large numbers (INR), Unicode names, part-timers, terminated staff |
| **Deterministic** | Same `--seed` gives an identical dataset (only the demo users' password hashes differ, by their random salt), guarded by checksum tests |
| **Fast** | < 5 s locally for 10k employees + ~24k salary records + ~40k components (measured 2.9–3.5 s, [19-performance.md](19-performance.md) §9) |
| **Honest** | All data is synthetic. The planted patterns are documented here (§8) and in the code (`seed/generator.py`, `_plant_story`), not hidden |

All values marked **(proposed)** are starting points to tune during milestone 6 ([18-implementation-plan.md](18-implementation-plan.md)). Final values are recorded in `backend/src/salary_api/seed/seed_config.py`, a pure-data module, so tuning never touches generator logic.

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

**35 roles.** Inside a department, each country's headcount is split across roles by weights that favour the individual-contributor roles **(proposed)**, e.g. Software Engineer 35% of Engineering (largest remainder, so the split is exact). The weights are in `seed_config.py`.

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

Each country's levels are split exactly by this pyramid (largest remainder), shuffled, and paired with the role slots. If a level is outside the role's allowed range, it is **clamped** to the nearest allowed level. Clamping distorts the pyramid, most at the top (only six roles allow L6); the seed CLI reports the final distribution. For `--seed 42`: L1 1,807 · L2 3,389 · L3 2,691 · L4 1,637 · L5 453 · L6 23.

Employment type: **90% FULL_TIME, 6% PART_TIME, 4% CONTRACTOR**, split exactly per country (largest remainder) and shuffled.

Status **(proposed)**: 3% `TERMINATED` (rounded half-even, chosen at random), with `termination_date` after `hire_date` and on or before the seed anchor date. Their salary history ends by the termination date. This exercises the default "active only" filter.

## 5. Base pay formula

```
reference_usd   = LEVEL_BAND_USD[level] × FAMILY_MULT[role.family] × COUNTRY_FACTOR[country]
noise           = exp( Normal(μ = 0, σ = 0.06) ), within [0.89, 1.12]  # log-normal, ±~6%
base_usd        = reference_usd × noise
base_local      = base_usd / FX_RATE_TO_USD[currency]
part-time       → base_local × Uniform(0.5, 0.8)                  # proposed: implied FTE not stored
base_local      = round_to(base_local, ROUNDING[currency])        # 1,000 local; 10,000 for INR and JPY
```

**Why the noise is narrow (decided).** A draw outside [0.89, 1.12] (about 1.9 σ each way, symmetric in log terms) is drawn again, so there is no pile at a bound. With σ = 0.12 and no bounds, noise alone flagged about 9 % of full-timers and pushed small teams (France Finance, 0.945) below the 0.95 threshold, which buried the planted story (§8). Now, after rounding, a full-timer always sits at 0.86–1.16 of the band mid, and a DE Customer Success one at 0.81 or more after the −8 % gap, in every one of the 1,360 bands (a unit test checks each band): noise alone never flags anyone, for any seed.

`round_to` rounds half-even to a multiple of the unit, and never below one unit. Base pay is rounded once, after the part-time factor. Uniform draws are integer steps on a 0.0001 grid, and the normal draw is cut to four decimals before `Decimal.exp`, so platform float maths cannot change a salary.

Country factors (relative to the US in USD terms, **proposed**; tuned to look plausible, not market data):

| US | GB | DE | FR | CA | AU | SG | JP | IN | BR |
|---|---|---|---|---|---|---|---|---|---|
| 1.00 | 0.75 | 0.75 | 0.68 | 0.80 | 0.80 | 0.80 | 0.62 | 0.28 | 0.30 |

Worked example: **India, Software Engineer, L2**: 95,000 × 1.00 × 0.28 = 26,600 USD → ÷ 0.0120 = 2,216,667 INR → noise → rounded to the nearest 10,000, e.g. **₹22,20,000**.

All arithmetic is in `Decimal`, and the result is converted once to integer minor units ([adr/0004-money-integer-minor-units.md](adr/0004-money-integer-minor-units.md)).

## 6. Compensation components

Stored as `salary_components` rows on each salary record ([adr/0010-compensation-components.md](adr/0010-compensation-components.md)). Component names: `HRA`, `Special allowance`, `Meal`, `Transport`, `Target bonus`. Percentages are rounded half-even to the minor unit.

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

Each employee gets **1 to 10 salary records**, about 97% of them 6 or fewer (append-only; [adr/0006-append-only-salary-history.md](adr/0006-append-only-salary-history.md)), **about 24k in total** for 10k employees (24,058 for `--seed 42`). Each record carries a `job_role_id` + `level` **snapshot**, so history can show "L2 → L3, Promotion, +12%".

**Back-casting (proposed)** keeps current pay on the bands. The current base is generated first (§5), then history is walked **backwards** from today:

1. **Hire date:** tenure ~ Exponential(mean 3.5 years), truncated at 11 years (drawn from the truncated distribution, so no pile of hires on the cap date; the mean after truncation is about 3.0 years), and at least one day before the seed anchor date. Hire dates fall between 2015-10-01 and 2026-09-30.
2. **Anniversaries:** on each work anniversary before the anchor date:
   - with probability **0.55** there is a **MERIT** raise of Uniform(2%, 6%);
   - once per employee, with probability **15%** for an employee with at least one anniversary and a level below theirs in the role's range (about 7% of all employees for `--seed 42`: 705), a **PROMOTION** of Uniform(10%, 15%) on one random anniversary (instead of a merit raise that year), and level − 1 going back in time (only if the earlier level is still in the role's allowed range).
3. A small number of **MARKET_ADJUSTMENT** (+5–10%) and **CORRECTION** (−3% to +3%) records: each employee gets one with probability **1%** and **0.5%** **(proposed)**, on a random day after the hire date.
4. Walking back divides the base by each raise factor. The earliest record is the **HIRE** record at `hire_date`.
5. Amounts are re-rounded at each step to the currency's rounding unit, and moved at least one unit the other way when rounding would undo the change (a 2 % raise on 19 units rounds back to 19). A CORRECTION never draws exactly 0 %. So every record changes the base: a raise always raises, a cut always cuts. Components are recomputed per record from the rules in §6, using that record's level.
6. `changed_by` = `null` (seeded history has no acting user); reasons use the enum `HIRE`, `PROMOTION`, `MERIT`, `MARKET_ADJUSTMENT`, `CORRECTION`.

This guarantees the current distribution matches §5. The raises insight ([09-insights-pay-equity.md](09-insights-pay-equity.md) §3.7) gets a realistic spread. The history's random draws depend only on dates and levels, never on amounts, so the demo story (§8) scales amounts without changing any salary event.

## 8. Demo story (planted, documented patterns)

The data is planted so pay equity and "Ask about pay" have **real findings** to show in the demo video ([10-ai-ask-design.md](10-ai-ask-design.md)):

| Pattern | Mechanics | Where it shows up |
|---|---|---|
| **~2% individual outliers** | 2% of FT active employees (rounded half-even, chosen by RNG): 60% get a base of their **band mid** × Uniform(0.65, 0.75) (**underpaid**), 40% × Uniform(1.30, 1.45) (**overpaid**). Set from the band mid, not the noisy base and not on top of the DE gap below, so every outlier is flagged whatever its noise. Applied **before** back-casting, so the whole history scales consistently | Pay-equity outlier flags (compa-ratio < 0.8 or > 1.2) |
| **Customer Success in Germany ~8% under band** | Every DE employee in a Customer Success role: current base × 0.92 | Pay-equity department rollup (median compa-ratio vs band ≈ 0.92); Ask: "Are we underpaying anyone in Germany?" |

> **Detectability (decided).** Compa-ratio is measured against the **pay band midpoint**, not the cohort's own median ([09-insights-pay-equity.md](09-insights-pay-equity.md) §3.8). Bands are seeded from the **pre-noise reference formula** in §5 (`mid` = reference × factors → local currency; `min` = 0.8 × mid; `max` = 1.2 × mid), so they are independent of the generated salaries. The team-wide −8% in DE Customer Success therefore shows as a department median compa-ratio ≈ 0.92 (below the 0.95 threshold), while normal departments sit ≈ 1.00 (log-normal noise has median 1). Individual outliers (×0.65–0.75 / ×1.30–1.45) fall outside 0.8–1.2 and are flagged.

**Pay bands seeded:** one row in `pay_bands` per job role × allowed level × country (136 role-levels from §3 × 10 countries ≈ 1,360 rows), `effective_from` = 2026-01-01 **(proposed)**. A test asserts every active employee has a band.

Both patterns can be switched off (`--no-story`) for tests that need a "clean" distribution. The story draws from its own child RNG, so with and without it the people and salary events are the same and only the planted amounts differ (a unit test checks this).

**Measured for `--seed 42 --employees 10000`** (checked by `tests/integration/test_seed_full.py` with the `domain/pay_equity` functions, across all countries):

| | Flagged UNDERPAID | Flagged OVERPAID | Teams (department × country) below 0.95 |
|---|---|---|---|
| `--no-story` | 0 | 0 | none (lowest: Marketing BR 0.974) |
| with the story | 104, exactly the planted ones | 70, exactly the planted ones | only Customer Success DE, median **0.929** (next lowest: Marketing BR 0.974) |

Before the noise was narrowed (σ = 0.12, §5), noise alone flagged 818 full-timers, the story run flagged 975 of which only 175 were planted, and France's Finance team sat at 0.945, below the threshold by chance.

## 9. Names and emails

Generated with **Faker**, one locale per country (`use_weighting=False`: every listed name is equally likely, and generation is about 20× faster):

| Country | Faker locale | Notes |
|---|---|---|
| US | `en_US` | |
| IN | `en_IN` | |
| GB | `en_GB` | |
| DE | `de_DE` | `Müller`, `Jürgen`: tests Unicode search |
| FR | `fr_FR` | `Élodie`, `François` |
| CA | `en_CA` | |
| SG | **Curated name lists** in `seed_config.py` (decided): 40 first and 31 last names across Chinese (romanized: Tan, Lim, Ng, Wei Ling…), Malay (Nur Aisyah, Muhammad Hafiz…) and Indian (Priya, Ramasamy…) origins. An origin is picked by weight (75 / 15 / 10), then a first and a last name of that origin, with a name RNG seeded like Faker's | Faker has no `en_SG`, and mixing other locales gives unrealistic names. A small fixed list is deterministic and realistic |
| AU | `en_AU` | |
| JP | `ja_JP` | Display name in kanji (e.g. 佐藤 花子); email from `romanized` names |
| BR | `pt_BR` | `José`, `Conceição` |

- `employee_code`: sequential `ACME-000001` … `ACME-010000`, in hire-date order (the longest-serving employee is `ACME-000001`).
- `email`: `first.last.<last 4 digits of code>@acme.example`, ASCII-folded (NFKD + strip accents, letters and digits only; romanized for JP). If that address is taken (same name, codes 10,000 apart), all six digits are used. `.example` is a **reserved domain** (RFC 2606), so no real person is ever emailed.
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

- With `APP_ENV=development` or `test`, a missing password falls back to its documented dev default (`backend/.env.example`: `change-me-admin`, `change-me-hr`, `change-me-viewer`).
- With `APP_ENV=production`, the app **refuses to start** with default or missing secrets, and the seed refuses a missing, blank, default or placeholder password (naming the variable, never the value). `make seed-turso` always runs the seed with `APP_ENV=production`.
- The **deployed demo's** credentials are shared in the README and the submission email (synthetic data only), so reviewers can log in as each role and see Viewer masking ([08-security-rbac.md](08-security-rbac.md)).

## 12. Determinism

| Mechanism | Detail |
|---|---|
| Single RNG | `rng = random.Random(seed)` passed explicitly to every generator function; no global `random`. The demo story and the salary history draw from child RNGs seeded from it, so `--no-story` and `--no-history` change only what they switch off |
| Names | One `Faker(locale)` instance per country, each `seed_instance(seed + country_index)`; Singapore's curated names use `random.Random(seed + country_index)`. Names never draw from the main RNG, so they cannot change a salary |
| Fixed anchor date | `SEED_ANCHOR_DATE = 2026-10-01` (config). All dates are relative to it, **not** to `today()`, so re-running next month gives identical data |
| Stable iteration | Countries, departments, and roles are iterated in config order (lists, not sets) |
| Exact allocation | Largest-remainder rounding for countries, departments, levels, and types |
| No wall-clock or UUID randomness | IDs are integers assigned in generation order; every timestamp is midnight UTC of a seeded date |

**Checksum test** ([14-testing-strategy.md](14-testing-strategy.md)):

- Generate with `--seed 42 --employees 10000` into in-memory SQLite.
- Assert exact counts per country (table in §2) and per department.
- Assert two `sha256` checksums equal **golden values** committed in the tests (`tests/seed_checks.py` computes them):
  - employees: the sorted tuples `(employee_code, country, job_role, level, employment_type, current_base_minor, current_total_minor, first_name, last_name, email, hire_date, status, termination_date)`;
  - history: every salary record `(employee_code, effective_date, reason, level, base_minor, total_minor)` followed by its components `type:name:amount_minor` in ID order, one sorted line per record.
- Assert the 10k counts: 24,058 salary records, 39,570 components, 300 terminated.
- Names are in the goldens, so a Faker upgrade that changes its name lists means updating them (with the reason in the commit message).
- Assert invariants: every employee has ≥ 1 salary record, the latest record matches the denormalized current salary, no amount ≤ 0, JPY amounts are whole yen, every currency has an FX rate, every email is unique.
- A fast variant with `--employees 200` (golden in `tests/integration/test_seed.py`) and the full 10k check (golden in `tests/integration/test_seed_full.py`) both run in the default suite: the 10k seed takes about 2.5 s in memory, and its tests share one xdist group, so a run builds it once. `make test` and CI therefore run it; there is no separate slow job.

If the generator logic changes on purpose, the golden checksums and counts are updated **in the same commit**, with the reason in the commit message.

## 13. Loading

### 13.1 Local / tests

- Schema via Alembic (`alembic upgrade head`, run by the seed itself on the target database), then the loader inserts with **SQLAlchemy Core `insert()` executemany in chunks of 1,000**, with IDs pre-allocated in Python, all in **one transaction** (`BEGIN IMMEDIATE`), so a failed seed leaves nothing behind. Employees go in first without their current record, then the salary history, then the link, as the employee service does.
- SQLite pragmas: `journal_mode=WAL` and `foreign_keys=ON` (set for every connection by `core/db.py`). `synchronous` is left as it is: the seed commits once.
- `--reset` deletes every row of every table first, in the same transaction. On SQLite it defers foreign-key checks to the commit and deletes employees before their salary records, so no deletion scans the employees table.
- Target: **< 5 s** for 10k employees on a laptop (measured and recorded in [19-performance.md](19-performance.md)).

### 13.2 Turso (production)

Inserting ~80k rows one network round-trip at a time into a remote DB is slow. The seed therefore builds a local file and uploads it:

1. `make seed-turso` → deletes any old `build/seed.db`, runs migrations + seed into a fresh `build/seed.db` with `APP_ENV=production` (real `SEED_*_PASSWORD` values required), then a WAL checkpoint, so it is a single self-contained file. It prints the next command and never calls Turso.
2. `turso db create salary-prod --from-file build/seed.db` (first time), **or** for a re-seed: destroy and re-create (demo data only; documented; check the auth token still works afterwards).
3. Verify: row counts via `turso db shell salary-prod "select count(*) from employees"` and the `/api/v1/health` endpoint.
4. Alembic's version table travels with the file, so later migrations apply normally.

Exact Turso CLI flags and file-size limits are **verified during the milestone 1 deploy spike** ([17-deployment.md](17-deployment.md)). The fallback (Neon Postgres) seeds via the normal insert path against the pooled URL.

## 14. CLI

```bash
# local dev: backend/dev.db (the default DATABASE_URL is sqlite:///./dev.db)
make seed                                   # = uv run python -m salary_api.seed --seed 42 --employees 10000 --reset --db-url sqlite:///./dev.db

# explicit
uv run python -m salary_api.seed \
  --seed 42 \
  --employees 10000 \
  --reset \                 # drop + recreate data (refuses on APP_ENV=production unless --force-demo)
  --no-story \              # disable demo-story distortions
  --no-history \            # one HIRE record per employee (fast tests)
  --force-demo \            # allow --reset with APP_ENV=production (demo data only)
  --db-url sqlite:///../build/seed.db   # default: DATABASE_URL

# build the Turso upload file
make seed-turso
```

Output: a summary table (counts per status, country, department, level, and type; salary records; components; pay bands; FX rates; users; what the demo story planted) and the time of each phase (users, migrate, generate, insert) and in total. A refusal prints the reason and exits with status 2 before anything is changed: unsafe production settings are refused before the database is even opened, and a database that has data (without `--reset`) before it is migrated.

## 15. Open questions

- All numeric parameters marked **(proposed)**: the values in `seed_config.py`; tune them there (and update the golden checksums in the same commit).
- ~~Singapore name locales~~ **Decided:** curated name lists (§9).
- How the DE Customer Success pattern is surfaced: **TBD** (milestone 7).
- Terminated share ~3% **(proposed)**.
