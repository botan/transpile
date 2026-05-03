# transpile

Transpile SQL files in place from a file or directory tree.

## Quick Start

```bash
uv run transpile path/to/sql-or-dir --read postgres --write snowflake
```

```bash
uv run transpile --dialects
```

## Behavior

- `TARGET` may be a single file or a directory (walked recursively).
- By default, only `*.sql` files are processed.
- Processing continues on per-file failures and prints a final summary.

## Flags

- `--read` / `--write` (required): source and target SQL dialects.
- `--pretty` / `--no-pretty`: format transpiled SQL output.
- `--exclude` (repeatable): exclude glob patterns.
- `--diff`: print unified diffs for changed files.
- `--dialects`: print all acceptable SQL dialect names and exit.
