---
name: new-module
description: Use when adding a new backend feature slice under backend/src/salary_api/modules/. Creates the router, schemas, service, repository and models skeleton that mirrors existing modules, plus a first failing test, then hands over to /tdd.
---

# /new-module <name>

1. Read an existing module (e.g. `backend/src/salary_api/modules/employees/`) and mirror its conventions.
   Don't invent a new pattern. Layering rules: [docs/05-architecture.md](../../../docs/05-architecture.md) §5.
2. Create `backend/src/salary_api/modules/<name>/{__init__,router,schemas,service,repository,models}.py`
   with minimal typed skeletons (only the files the module needs).
3. Create `backend/tests/unit/test_<name>_<topic>.py` and `backend/tests/integration/test_<name>_api.py`
   with **one failing test** that describes the first behaviour.
4. Register the router in the app factory (`main.py`) under `/api/v1`. Add each new endpoint to
   `tests/integration/test_authz_matrix.py` with its permission (it fails until the permission is declared).
5. If there are models, create an Alembic revision (`uv run alembic revision --autogenerate -m "add <name>"`)
   and review it by hand.
6. Commit the skeleton and failing test as `test(<name>): <first behaviour>`.
7. Hand over to `/tdd` for the first behaviour.
