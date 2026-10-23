# ADR-0003: Synchronous SQLAlchemy, `NullPool` in serverless, co-located regions

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

FastAPI supports both sync and async endpoints. The workload is light CRUD and aggregate reads over about 10k employees. Production runs FastAPI as **Vercel serverless functions** (see [ADR-0016](0016-deploy-vercel-turso.md)), where instances are short-lived and may be frozen between requests. The database is remote (Turso).

## Decision drivers

- Simplicity and testability (TDD is a core evaluation criterion).
- Correctness under serverless execution.
- Low latency for remote database calls.

## Considered options

1. **Sync SQLAlchemy sessions** in sync path functions (FastAPI runs them in its threadpool).
2. **Async SQLAlchemy** (`AsyncSession`, aiosqlite/asyncpg).

### Option 1
- Pros: simplest mental model; plain pytest fixtures; no event-loop pitfalls (lazy loading in async, `greenlet` errors, mixed sync and async code). The threadpool is plenty for this load.
- Cons: a thread per in-flight request; less trendy.

### Option 2
- Pros: better at very high concurrency of I/O-bound requests.
- Cons: more complex tests and sessions; async drivers for libSQL are even less mature; no measurable benefit at this scale.

## Decision

**Option 1, sync SQLAlchemy**, plus:
- **`NullPool` in serverless.** Each invocation opens and closes its connection, because frozen function instances must not hold pooled connections. Locally, the default pool is used.
- **Vercel function region = Turso database region**, to keep per-query round-trips short.
- One session per request via a FastAPI dependency. The **service layer owns the transaction boundary**, so a domain write and its audit event commit together (see [ADR-0011](0011-audit-events.md)).

## Consequences

### Positive
- Straightforward code and tests. Easy to explain in the interview.
- No stale pooled connections across function freezes.

### Negative / risks
- Opening a connection per request adds latency. That's acceptable for an HR tool, and measured in [19-performance.md](../19-performance.md).
- If concurrency ever grew by orders of magnitude, async (or a long-running server) would need revisiting. Documented as a scaling path.

## Links

- [05-architecture.md](../05-architecture.md), [17-deployment.md](../17-deployment.md), [19-performance.md](../19-performance.md)
