# transpile

Transpile SQL files in place, from a file path or an entire directory tree.

## Usage

```bash
uv run transpile path/to/sql-or-dir --read postgres --write snowflake
```

## Behavior

- `TARGET` can be a single file or a directory.
- Directories are walked recursively.
- Only `*.sql` files are processed by default.
- The command keeps running if individual files fail and prints a final summary.

## Options

- `--read`: source SQL dialect (required)
- `--write`: target SQL dialect (required)
- `--pretty` / `--no-pretty`: format transpiled SQL output
- `--exclude`: exclude glob(s), repeatable
- `--diff`: print unified diffs for changed files

## Exit Codes

- `0`: success
- `1`: at least one file failed to transpile
