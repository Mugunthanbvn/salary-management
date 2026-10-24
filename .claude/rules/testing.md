---
paths:
  - "backend/tests/**"
  - "frontend/**/*.test.ts*"
  - "frontend/e2e/**"
---

# Testing rules

Source: [docs/14-testing-strategy.md](../../docs/14-testing-strategy.md).

- **One behaviour per test.** Name it like a requirement: `test_<who>_<does>_<outcome>`,
  e.g. `test_viewer_cannot_see_individual_salary`.
- **Arrange, act, assert**, in that order, separated by a blank line.
- **Factories over fixtures with hidden data.** Use the builders in `tests/factories.py` and state only the
  fields that matter to the test (`make_employee(session, country="DE")`).
- **Deterministic:** freeze time with `time-machine`; pass `random.Random(seed)`; no network, no `sleep`;
  no dependence on test order (pytest-randomly shuffles it).
- **Red must be meaningful:** the test fails on the behaviour under test, not on a typo or broken fixture.
- **Every endpoint is in the authz matrix** (`tests/integration/test_authz_matrix.py`) for every role.
- **Parametrize tables** of cases (`pytest.mark.parametrize`, `it.each`) instead of copy-pasted tests.
- Assert on the API contract: status code, problem+json `type` slug, and the response body shape.
- Frontend: query by role and label (RTL), not by class or test id where avoidable; MSW handlers use the generated types.
- Never weaken, skip or delete a test to get green. Fix the code or the test's real mistake.
