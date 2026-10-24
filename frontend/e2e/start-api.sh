#!/usr/bin/env bash
# Start the FastAPI app for the Playwright smoke flow (playwright.config.ts webServer):
# a fresh SQLite file in the temp dir, a small deterministic seed, then uvicorn on E2E_API_PORT.
# Every setting is passed explicitly, so the run does not depend on backend/.env.
set -euo pipefail

port="${E2E_API_PORT:-8100}"
db_file="${TMPDIR:-/tmp}/acme-salary-e2e.db"
db_url="sqlite:///${db_file}"

cd "$(dirname "$0")/../../backend"
rm -f "$db_file" "$db_file-wal" "$db_file-shm"

export APP_ENV=development
export DATABASE_URL="$db_url"
export JWT_SECRET=e2e-only-secret-not-for-any-real-deployment
export COOKIE_SECURE=false
export CORS_ORIGINS=
export LLM_API_KEY=
export LOG_LEVEL=WARNING
export SEED_ADMIN_PASSWORD=change-me-admin
export SEED_HR_PASSWORD=change-me-hr
export SEED_VIEWER_PASSWORD=change-me-viewer

uv run python -m salary_api.seed --seed 42 --employees 300 --reset --db-url "$db_url"
exec uv run uvicorn salary_api.main:app --host 127.0.0.1 --port "$port"
