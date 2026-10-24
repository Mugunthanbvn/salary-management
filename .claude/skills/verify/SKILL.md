---
name: verify
description: Use before saying work is done, before a commit that claims green, and before merging or opening a PR. Runs make verify (lint, typecheck, tests, API drift) and reports each check's result.
---

# /verify

1. Run `make verify` from the repo root.
2. If something fails, group the failures by tool: ruff, pyright, pytest (incl. coverage gate),
   eslint, prettier, tsc, vitest, API drift (`make api-sync` not run).
3. Report a short table: tool → pass/fail → the first relevant error lines (file:line and message).
4. Fix the failures and run `make verify` again until everything is green.
5. Never report "done" with a failing check. Never skip, disable, `# type: ignore`, `noqa` or weaken a check
   or test to get green. If a check itself is wrong, say so and fix its configuration explicitly.
