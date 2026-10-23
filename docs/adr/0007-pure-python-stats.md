# ADR-0007: Statistics (median, percentiles, compa-ratio) as pure Python domain functions

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

Insights need min/max/mean/median/P25/P75 per country, department, job role and cohort, plus compa-ratio for pay-equity. SQL engines differ here: Postgres has `percentile_cont`, SQLite has no percentile function. Computing percentiles differently in tests and prod is a known trap; one competitor verified percentiles only on Postgres.

## Decision drivers

- Identical results on SQLite and Postgres.
- Unit-testable without a database (fast, deterministic TDD).
- Adequate performance at 10k employees.

## Considered options

1. **SQL returns the (sorted) amounts per group; pure Python functions compute the statistics.**
2. **Dialect-specific SQL** (`percentile_cont` on PG, emulation on SQLite).
3. **Portable SQL percentiles via window functions** (`ROW_NUMBER`/`COUNT OVER`).

## Decision

**Option 1.**
- `domain/stats.py`: `median`, `percentile(values, p)` (one documented method: linear interpolation between closest ranks, the same definition as Postgres `percentile_cont`), `mean`, `min`/`max`, histogram bucketing. Integer and `Decimal` safe, never float for money.
- `domain/pay_equity.py`: compa-ratio = base ÷ pay-band midpoint (band per job role + level + country), outlier flags (<0.8 / >1.2), department rollup (median compa-ratio). The first draft used the cohort median as the benchmark. It was replaced because a cohort-wide gap moves the median too, so systemic underpayment would be invisible.
- Repositories return plain rows `(group_key, amount_minor)`. Simple `COUNT`/`SUM`/`MIN`/`MAX` aggregates can stay in SQL where portable.

## Consequences

### Positive
- Tested exhaustively with plain unit tests and Hypothesis properties (e.g. P25 ≤ median ≤ P75; the median of a constant list is that constant).
- Same numbers on every database, plus the Postgres CI job as a cross-check.

### Negative / risks
- Moves up to about 10k–30k integers into Python per request, which takes milliseconds. Not suitable at millions of rows. The scaling path (`percentile_cont`, materialized views, pre-aggregation) is documented in [19-performance.md](../19-performance.md).

## Links

- [09-insights-pay-equity.md](../09-insights-pay-equity.md), [14-testing-strategy.md](../14-testing-strategy.md), [ADR-0002](0002-sqlite-everywhere-turso.md)
