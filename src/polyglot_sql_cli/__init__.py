from pathlib import Path

import typer
from polyglot_sql import transpile

app = typer.Typer(add_completion=False)


def _fail(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


def _serialize_statements(statements: list[str]) -> str:
    cleaned = [statement.rstrip().rstrip(";") for statement in statements if statement.strip()]
    if not cleaned:
        return ""
    return ";\n".join(cleaned) + ";\n"


@app.command()
def cli(
    input_path: Path = typer.Argument(..., help="Path to a single .sql file."),
    read: str = typer.Option(..., "--read", "-r", help="Source SQL dialect."),
    write: str = typer.Option(..., "--write", "-w", help="Target SQL dialect."),
    pretty: bool = typer.Option(
        False,
        "--pretty/--no-pretty",
        help="Pretty format transpiled SQL output.",
    ),
) -> None:
    if not input_path.exists():
        _fail(f"Input file does not exist: {input_path}")
    if not input_path.is_file():
        _fail(f"Input path is not a file: {input_path}")
    if input_path.suffix.lower() != ".sql":
        _fail(f"Input file must have a .sql extension: {input_path}")

    sql = input_path.read_text(encoding="utf-8")

    try:
        result = transpile(sql, read=read, write=write, pretty=pretty)
    except Exception as exc:
        _fail(f"Transpile failed ({read} -> {write}): {exc}")

    output_sql = _serialize_statements(result)
    if not output_sql:
        _fail("Transpile produced empty output.")

    input_path.write_text(output_sql, encoding="utf-8")


def main() -> None:
    app()
