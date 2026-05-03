# polyglot-sql-cli

Transpile SQL files in place, from a file path or an entire directory tree.

## Usage

```bash
uv run polyglot path/to/sql-or-dir --read postgres --write snowflake
```

## Behavior

- `TARGET` can be a single file or a directory.
- Directories are walked recursively by default.
- Only `*.sql` files are processed by default.
- The command keeps running if individual files fail and prints a final summary.

## Options

- `--read` / `-r`: source SQL dialect (required)
- `--write` / `-w`: target SQL dialect (required)
- `--pretty` / `--no-pretty`: format transpiled SQL output
- `--recursive` / `--no-recursive`: recursive directory walk (default: recursive)
- `--include`: include glob(s), repeatable (default: `*.sql`)
- `--exclude`: exclude glob(s), repeatable
- `--ignore-file`: ignore file path (default: `.polyglotignore` next to target)
- `--check`: no-write mode; exits non-zero when files would change
- `--diff`: print unified diffs for changed files

## Exit Codes

- `0`: success
- `1`: at least one file failed to transpile
- `2`: `--check` mode found files that would change
