# ACME Salary Management: one entry point for every task (docs/15-tooling-devex.md section 6).
# `make help` lists the targets. Git hooks, `make verify` and CI run the same commands.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

# Deterministic tests and tools.
export TZ := UTC
export LC_ALL := C.UTF-8
export PYTHONHASHSEED := 0
export COREPACK_ENABLE_DOWNLOAD_PROMPT := 0

BACKEND := backend
FRONTEND := frontend
# Run pnpm from inside frontend/ so corepack reads its packageManager pin (pnpm --dir from the root does not).
PNPM := cd $(FRONTEND) && pnpm
API_GENERATED := $(FRONTEND)/openapi.json $(FRONTEND)/src/lib/api/schema.d.ts

.PHONY: help setup dev migrate seed seed-turso fmt fmt-backend fmt-frontend lint lint-backend lint-frontend \
	typecheck typecheck-backend typecheck-frontend test test-backend test-frontend e2e \
	build-frontend api-sync api-drift verify verify-backend clean

help: ## List the targets
	@awk 'BEGIN { FS = ":.*## " } /^[a-z][a-z0-9-]*:.*## / { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Install everything once after clone: uv sync, pnpm install, git hooks, .env files
	cd $(BACKEND) && uv sync
	corepack enable || echo "corepack enable failed (it may need sudo); continuing with the pnpm on PATH"
	$(PNPM) install
	cd $(BACKEND) && uv run lefthook install
	@for app in $(BACKEND) $(FRONTEND); do \
	  if [ -f "$$app/.env.example" ] && [ ! -f "$$app/.env" ]; then \
	    cp "$$app/.env.example" "$$app/.env" && echo "Created $$app/.env from $$app/.env.example"; \
	  fi; \
	done

dev: migrate ## Run the API (:8000) and the web app (:3000) on backend/dev.db; Ctrl-C stops both
	@echo "API http://localhost:8000/api/v1/docs   web http://localhost:3000   (Ctrl-C stops both)"
	@# Portable (bash 3.2, make 3.81): on Ctrl-C or exit, stop the whole process group.
	@# The trap resets itself first, so its own SIGTERM does not run it again.
	@trap 'trap - INT TERM EXIT; kill 0' INT TERM EXIT; \
	  (cd $(BACKEND) && exec uv run uvicorn salary_api.main:app --reload --port 8000) & \
	  ($(PNPM) dev) & \
	  wait

migrate: ## Apply database migrations (alembic upgrade head) to DATABASE_URL
	cd $(BACKEND) && uv run alembic upgrade head

# The deterministic demo data (docs/12-seed-data.md). The seed runs `alembic upgrade head` itself.
SEED_ARGS := --seed 42 --employees 10000
SEED_FILE := build/seed.db

seed: ## Replace backend/dev.db data with the 10k demo seed (--seed 42); prints counts and timings
	cd $(BACKEND) && uv run python -m salary_api.seed $(SEED_ARGS) --reset --db-url sqlite:///./dev.db

seed-turso: ## Build build/seed.db for Turso (needs real SEED_*_PASSWORD); prints, never runs, the upload
	mkdir -p $(dir $(SEED_FILE))
	rm -f $(SEED_FILE) $(SEED_FILE)-wal $(SEED_FILE)-shm
	@# APP_ENV=production: the seed refuses default or missing demo passwords.
	cd $(BACKEND) && APP_ENV=production uv run python -m salary_api.seed $(SEED_ARGS) \
	  --db-url sqlite:///../$(SEED_FILE)
	@echo ""
	@echo "Built $(SEED_FILE) (one self-contained file). To create the production database, run:"
	@echo "  turso db create salary-prod --from-file $(SEED_FILE)"

fmt: fmt-backend fmt-frontend ## Format and auto-fix all code

fmt-backend: ## ruff format + ruff check --fix
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

fmt-frontend: ## prettier --write
	$(PNPM) format

lint: lint-backend lint-frontend ## Lint and check formatting (backend + frontend)

lint-backend: ## ruff check + ruff format --check
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .

lint-frontend: ## eslint + prettier --check
	$(PNPM) lint
	$(PNPM) format:check

typecheck: typecheck-backend typecheck-frontend ## Type-check (pyright + tsc)

typecheck-backend: ## pyright (strict on src/)
	cd $(BACKEND) && uv run pyright

typecheck-frontend: ## tsc --noEmit
	$(PNPM) typecheck

test: test-backend test-frontend ## Run all unit and integration tests

test-backend: ## pytest (parallel, in-memory SQLite) + the 90 % coverage gate
	cd $(BACKEND) && uv run pytest --cov --cov-report=term-missing:skip-covered
	cd $(BACKEND) && uv run python scripts/coverage_gate.py

test-frontend: ## vitest run
	$(PNPM) test

e2e: ## Playwright smoke flow
	$(PNPM) e2e

build-frontend: ## next build
	$(PNPM) build

api-sync: ## Export openapi.json, regenerate frontend/src/lib/api/schema.d.ts, then tsc
	cd $(BACKEND) && uv run python -m salary_api.openapi ../$(FRONTEND)/openapi.json
	$(PNPM) api:types
	$(PNPM) typecheck

api-drift: ## Fail if the generated API client was stale (in CI: also if it is not committed)
	@if [ "$${CI:-}" = "true" ]; then \
	  $(MAKE) api-sync || exit 1; \
	  if [ -n "$$(git status --porcelain -- $(API_GENERATED))" ]; then \
	    git --no-pager diff -- $(API_GENERATED); \
	    echo "API drift: run 'make api-sync' and commit $(API_GENERATED)"; \
	    exit 1; \
	  fi; \
	else \
	  snapshot="$$(mktemp -d)"; \
	  for file in $(API_GENERATED); do \
	    if [ -f "$$file" ]; then cp "$$file" "$$snapshot/$$(basename "$$file")"; fi; \
	  done; \
	  $(MAKE) api-sync || { rm -rf "$$snapshot"; exit 1; }; \
	  stale=""; \
	  for file in $(API_GENERATED); do \
	    cmp -s "$$file" "$$snapshot/$$(basename "$$file")" || stale="$$stale $$file"; \
	  done; \
	  rm -rf "$$snapshot"; \
	  if [ -n "$$stale" ]; then \
	    echo "Generated API files were stale; regenerated, commit them:$$stale"; \
	    exit 1; \
	  fi; \
	fi

verify: lint typecheck test build-frontend api-drift ## Everything CI checks: run before saying done

verify-backend: lint-backend typecheck-backend test-backend ## The backend half of verify

clean: ## Remove virtualenv, node_modules, build output, coverage and local databases
	rm -rf $(BACKEND)/.venv $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/htmlcov
	rm -f $(BACKEND)/.coverage $(BACKEND)/.coverage.* $(BACKEND)/coverage.xml $(BACKEND)/dev.db*
	rm -rf $(FRONTEND)/node_modules $(FRONTEND)/.next $(FRONTEND)/coverage build
