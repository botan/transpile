# polyglot-sql-cli

Transpile a single `.sql` file from one SQL dialect to another in place.

## Usage

```bash
uv run polyglot-sql-cli path/to/query.sql --read postgres --write snowflake --pretty
```

Required arguments:
- `input_path`: path to one `.sql` file
- `--read` / `-r`: source dialect
- `--write` / `-w`: target dialect

Optional arguments:
- `--pretty` / `--no-pretty`: format transpiled output

The command overwrites the input file with transpiled SQL and exits non-zero on invalid paths, non-`.sql` files, empty transpile output, or transpiler errors.
