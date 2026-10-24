---
name: tdd
description: Use when implementing any behaviour, feature or bug fix in backend or frontend code. Runs one red-green-refactor cycle for a single behaviour, with separate test/feat/refactor commits so TDD is visible in git history.
---

# /tdd <behaviour>

One behaviour per cycle. Never batch several behaviours. See [docs/14-testing-strategy.md](../../../docs/14-testing-strategy.md) §2–§3.

1. Restate the behaviour as one acceptance criterion. Pick the lowest test layer that can prove it:
   domain unit (no DB) → service (in-memory SQLite) → API (TestClient) → frontend unit (Vitest) → e2e.
2. **Red:** write **one** failing test with a descriptive name (`test_<who>_<does>_<outcome>`). Nothing else.
3. Run only that test and **show that it fails for the expected reason** (the assertion or the missing symbol
   under test). If it fails for another reason (import error, fixture bug, typo), fix the test first.
   - Backend: `cd backend && uv run pytest <path>::<test_name> -q`
   - Frontend: `cd frontend && pnpm vitest run <file> -t "<name>"`
4. Commit the red step with `/commit`: `test(<scope>): <behaviour>`. A bug fix starts with `test(<scope>): reproduce <bug>`.
5. **Green:** write the minimum production code to pass. No speculative parameters, no "while I'm here".
   Run the test, then the module's suite.
6. Commit with `/commit`: `feat(<scope>): <behaviour>` (or `fix(<scope>): …`).
7. **Refactor on green:** names, duplication, extraction, in code and tests. Re-run the suite.
   If anything changed, commit `refactor(<scope>): <what>`.
8. Stop and present the next behaviour candidate. Trivial glue (e.g. registering a router) may be one `feat:` commit with its test.
