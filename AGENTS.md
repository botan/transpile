# Repository Guidelines

## Build, Test, and Development Commands
Use `uv` for all local workflows.
- `uv run transpile path/to/sql-or-dir --read postgres --write snowflake`: run the CLI locally.
- `uv run pytest`: run test suite.
- `uv run ruff check`: run lint checks.
- `uv run ty check`: run static type analysis.

If your environment blocks the default `uv` cache path, set a local cache (example: `UV_CACHE_DIR=.uv-cache uv build`).

## Coding Style & Naming Conventions
- Follow Python 3.13+ style with explicit modern type hints.
- Prefer small, focused helpers; internal helpers use a leading underscore (for example, `_candidate_files`).
- Run `ruff` and `ty` before making a commit or opening a PR.

## Change Scope Policy
- Default to surgical, minimal diffs that directly solve the requested task.
- Do not add new dependencies, helpers, docs updates, or broad refactors unless required for correctness or explicitly requested.
- Keep tests targeted: add or change tests only when needed to cover changed behavior or prevent regressions from that exact change.
- Preserve existing behavior and output unless the request explicitly asks for behavior changes.

## Commit
- `wt step comit` to create commits with a guided prompt.
