# ADR-0010: Compensation modelled as base salary plus a components table

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

Pay is rarely a single number. In India, for example, a typical package is base salary + HRA (house rent allowance) + special allowance + a target bonus. Comparing **base only** across countries can mislead: country A may pay a low base plus big allowances, country B a high base and no allowances. The candidate asked for a plain-language explanation of bonuses, allowances and components before choosing.

Worked example (Priya, engineer, India, yearly):

| Component | Amount |
|---|---|
| Base salary | ₹12,00,000 |
| HRA allowance | ₹4,80,000 |
| Transport allowance | ₹24,000 |
| Target bonus 10% of base | ₹1,20,000 |
| **Total compensation** | **₹18,24,000** |

## Decision drivers

- Answer "total compensation" questions correctly.
- Keep scope controlled (this is not a payroll or benefits system).
- Comparable metrics across countries.

## Considered options

1. **Base + components table** (`ALLOWANCE`, `BONUS_TARGET` rows per salary record).
2. Base + a single target-bonus % field.
3. Base salary only.

## Decision

**Option 1.**
- `salary_components(id, salary_record_id, type ALLOWANCE|BONUS_TARGET, name, amount_minor)`. Components belong to a salary record, so they are versioned with the salary history ([ADR-0006](0006-append-only-salary-history.md)).
- **Total comp** = base + Σ allowances + bonus target amount. It's denormalized as `employees.current_total_minor`, maintained by the salary service.
- **Annual is the stored value.** Monthly is a display toggle (÷12, formatted per the currency exponent).
- Insight endpoints accept `comp=base|total`.
- **Out of scope:** equity/RSUs, sales commission, overtime, non-cash benefits (insurance, pension). These are payroll and benefits territory.

## Consequences

### Positive
- Correct cross-country comparisons. Seed data can model realistic country-specific packages (IN HRA, FR meal, GB/DE transport).

### Negative / risks
- Bigger model, forms, import template and seed. More tests.
- A bonus *target* is not a bonus *paid*; the UI and docs label it "target".

## Links

- [06-data-model.md](../06-data-model.md), [09-insights-pay-equity.md](../09-insights-pay-equity.md), [12-seed-data.md](../12-seed-data.md), [11-import-export.md](../11-import-export.md)
