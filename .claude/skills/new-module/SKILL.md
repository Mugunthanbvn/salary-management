---
name: new-module
description: Use when adding a new backend feature slice under backend/src/salary_api/modules/. Creates an empty router, schemas, service, repository and models scaffold that mirrors existing modules, commits it as a chore, then hands over to /tdd for the first behaviour.
---

# /new-module <name>

1. Read an existing module (e.g. `backend/src/salary_api/modules/employees/`) and mirror its conventions.
   Don't invent a new pattern. Layering rules: [docs/05-architecture.md](../../../docs/05-architecture.md) §5.
2. Create `backend/src/salary_api/modules/<name>/{__init__,router,schemas,service,repository,models}.py`
   (only the files the module needs) as an **empty scaffold**: module docstring, imports, an `APIRouter`
   with its prefix and tags. No endpoints, no models, no business code.
3. Register the empty router in the app factory (`main.py`) under `/api/v1`.
4. Run `make verify` (lint and typecheck must pass), then commit with `/commit` as
   `chore(<name>): scaffold module`. The scaffold has no behaviour, so it is not a `test:` or `feat:` commit.
5. Hand over to `/tdd` for the first behaviour. Everything with behaviour comes through TDD from here:
   - the first failing test (`tests/unit/test_<name>_<topic>.py` or `tests/integration/test_<name>_api.py`);
   - each endpoint, with its permission and its row in `tests/integration/test_authz_matrix.py`;
   - models, when a test needs them, with an Alembic revision
     (`uv run alembic revision --autogenerate -m "add <name>"`) reviewed by hand.
