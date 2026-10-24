# ADR-0002: SQLite everywhere (local file, in-memory tests, Turso in production) behind the SQLAlchemy ORM

- **Status:** Accepted (2026-10-24 amendment: the Postgres CI job is cut from v1; it is added only if the deploy spike forces the Neon fallback)
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The brief asks for "a relational database of your choice, like SQLite" and a seed of **10,000 employees**. With roughly 24k salary records and 40k components, the whole dataset is about **5–10 MB** (the seeded file is 10.5 MB). Usage is low-concurrency: a handful of HR editors, not thousands of writers.

Production must be **free** and must keep data while reviewers look at it, possibly for weeks. Free serverless hosts (Vercel) have **no persistent disk**, so a plain SQLite file cannot live in production there.

The candidate explicitly wanted an ORM so the database can be swapped by **changing only the connection string**.

## Decision drivers

- Fits the actual scale and the brief's own suggestion.
- Zero setup for reviewers (`make setup && make dev`, no Docker, no DB server).
- One SQL dialect across dev, tests and prod, so statistics behave identically everywhere.
- $0 production hosting with persistent data and no sleeping.
- Portability to Postgres if the system grows.

## Considered options

1. **SQLite everywhere, with Turso (hosted libSQL/SQLite) in production.**
2. **Postgres everywhere** (docker-compose locally, testcontainers in tests, Neon in prod).
3. **SQLite in dev/test, Postgres (Neon) in prod.**
4. **SQLite file on a persistent volume** (Fly.io / Railway / own VM).

### Option 1: SQLite + Turso
- Pros: same dialect everywhere; trivial local setup; very fast in-memory tests. Turso's free tier (about 5 GB, 500M reads and 10M writes a month, no cold starts or sleeping) is far beyond our needs. Moving to Postgres stays a URL change thanks to the ORM.
- Cons: the Python driver for Turso is young. The original `sqlalchemy-libsql` repo was archived in June 2025 and work moved to the newer Turso binding with its own dialect. Remote round-trips per query add latency, so the function region must match the database region.

### Option 2: Postgres everywhere
- Pros: the most "production-looking" choice; rich SQL (`percentile_cont`).
- Cons: reviewers need Docker; tests are slower and depend on containers; more infrastructure to explain; over-engineered for about 10 MB.

### Option 3: SQLite dev/test, Postgres prod
- Pros: common pattern; free Neon tier.
- Cons: **dialect drift**. Medians and percentiles, `LIKE` case behaviour and type affinity all differ between the two, so tests prove less about prod. One competitor submission had exactly this gap (percentiles verified only on Postgres).

### Option 4: SQLite on a volume
- Pros: plain SQLite with the most mature driver.
- Cons: not free. Fly.io has no free tier for new users and Railway is trial-only; trial expiry could take the demo down mid-review. Self-hosting on the candidate's own VM was ruled out by the candidate (see [ADR-0016](0016-deploy-vercel-turso.md)).

## Decision

**Option 1.** SQLAlchemy 2.x ORM + Alembic, configured only through `DATABASE_URL`:

| Environment | URL (shape) |
|---|---|
| Local dev | `sqlite:///./dev.db` |
| Unit/integration tests | `sqlite://` (in-memory) |
| Production | `sqlite+libsql://<db>.turso.io?authToken=…&secure=true` (exact dialect string TBD by the day-1 deploy spike) |
| Portability proof (CI) | `postgresql+psycopg://…` (GitHub Actions service container) |

SQLite specifics are handled in code and covered by tests (see [06-data-model.md](../06-data-model.md)):
- `PRAGMA foreign_keys=ON` on every connection.
- WAL journal mode for local file databases.
- A lowercased `search_text` column, because SQLite's `LIKE` is only case-insensitive for ASCII (names like "Müller" and "Érica").
- Money stored as integers (see [ADR-0004](0004-money-integer-minor-units.md)).

## Consequences

### Positive
- Same behaviour in every environment. Reviewers can clone and run with no infrastructure.
- Fast, deterministic test suite.
- A small CI job runs the suite against Postgres, which *proves* the "swap by URL" claim instead of just asserting it.

### Negative / risks
- **Driver maturity risk.** Mitigation: milestone 1 includes a deploy spike that reads and writes through the Turso driver from a Vercel function. If it's flaky, fall back to **Neon Postgres** by changing `DATABASE_URL`, already covered by the Postgres CI job.
- SQLite allows one writer at a time. That's fine for an HR team; documented as a scaling limit in [19-performance.md](../19-performance.md).
- Seeding remotely row by row is slow, so the seed builds a local SQLite file and uploads it with `turso db create --from-file` (see [12-seed-data.md](../12-seed-data.md)).

## Links

- [ADR-0003](0003-sync-sqlalchemy-serverless.md), [ADR-0007](0007-pure-python-stats.md), [ADR-0016](0016-deploy-vercel-turso.md)
- [04-research.md](../04-research.md), [17-deployment.md](../17-deployment.md)
