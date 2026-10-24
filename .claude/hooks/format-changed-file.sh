#!/usr/bin/env bash
# PostToolUse formatter for Edit/Write (see docs/16-claude-code-setup.md §7.2).
#   backend/**/*.py                          -> ruff format + ruff check --fix
#   frontend/**/*.{ts,tsx,css,json,md}       -> prettier --write
# The project root is the nearest folder above the file that holds backend/pyproject.toml or
# frontend/package.json, so a file in a git worktree is formatted with that worktree's own tools.
# Input: the hook JSON on stdin. Exit 0 = done or nothing to do (also when the tool isn't installed yet).
# Exit 2 = the edit stays, but a formatter/linter problem is reported back to Claude on stderr.
set -u

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
elif command -v python3 >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | python3 -I -c '
import json, sys
try:
    print((json.load(sys.stdin).get("tool_input") or {}).get("file_path") or "")
except Exception:
    pass
' 2>/dev/null)"
else
  exit 0
fi

[ -n "${file:-}" ] || exit 0
case "$file" in
  /*) ;;
  *) file="${CLAUDE_PROJECT_DIR:-$PWD}/$file" ;;
esac
[ -f "$file" ] || exit 0
dir="$(cd "${file%/*}" 2>/dev/null && pwd)" || exit 0 # resolves "." and ".."
abs="$dir/${file##*/}"

root="$dir"
until [ -f "$root/backend/pyproject.toml" ] || [ -f "$root/frontend/package.json" ]; do
  [ -n "$root" ] || exit 0 # not inside a project
  root="${root%/*}"
done
rel="${abs#"$root"/}"

report() {
  printf 'format-changed-file: %s reported problems in %s:\n%s\n' "$1" "$rel" "$(printf '%s' "$2" | head -n 40)" >&2
  exit 2
}

case "$rel" in
  backend/.venv/* | */node_modules/* | frontend/.next/*)
    exit 0 ;;

  backend/*.py)
    command -v uv >/dev/null 2>&1 || exit 0
    [ -f "$root/backend/pyproject.toml" ] || exit 0
    [ -x "$root/backend/.venv/bin/ruff" ] || exit 0 # project ruff not installed yet (run make setup)
    cd "$root/backend" || exit 0
    out="$(uv run --quiet --no-sync ruff format "$abs" 2>&1)" || report "ruff format" "$out"
    # F401 (unused import) is ignored here: an import added in one edit is used in the next.
    # lefthook and CI still catch unused imports.
    out="$(uv run --quiet --no-sync ruff check --fix --ignore F401 "$abs" 2>&1)" || report "ruff check" "$out"
    ;;

  frontend/*.ts | frontend/*.tsx | frontend/*.css | frontend/*.json | frontend/*.md)
    [ -d "$root/frontend/node_modules" ] || exit 0
    prettier="$root/frontend/node_modules/.bin/prettier" # the binary 'pnpm prettier' runs
    [ -x "$prettier" ] || exit 0
    command -v node >/dev/null 2>&1 || exit 0
    cd "$root/frontend" || exit 0
    out="$("$prettier" --write --log-level warn "$abs" 2>&1)" || report "prettier" "$out"
    ;;
esac

exit 0
