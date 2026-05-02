# polyglot-sql-cli

Transpile a single SQL file from one SQL dialect to another in place.

## Usage

```bash
uv run polyglot path/to/query.sql --read postgres --write snowflake --pretty
```

Required arguments:
- `input_path`: path to one file to transpile in-place
- `--read` / `-r`: source dialect
- `--write` / `-w`: target dialect

Optional arguments:
- `--pretty` / `--no-pretty`: format transpiled output

The command overwrites the input file with transpiled SQL output from the engine.
