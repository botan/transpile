from pathlib import Path
from typing import Annotated

import typer
from polyglot_sql import transpile

app = typer.Typer(add_completion=False)


def _validate_sql_file(path: Path) -> Path:
    if path.suffix.lower() != ".sql":
        raise typer.BadParameter("Path must point to a .sql file.")
    return path


def _serialize_statements(statements: list[str]) -> str:
    cleaned = [statement.rstrip().rstrip(";") for statement in statements if statement.strip()]
    if not cleaned:
        return ""
    return ";\n".join(cleaned) + ";\n"


@app.command()
def cli(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a single .sql file.",
            exists=True,
            dir_okay=False,
            readable=True,
            writable=True,
            resolve_path=True,
            callback=_validate_sql_file,
        ),
    ],
    read: Annotated[str, typer.Option("--read", "-r", help="Source SQL dialect.")],
    write: Annotated[str, typer.Option("--write", "-w", help="Target SQL dialect.")],
    pretty: Annotated[
        bool,
        typer.Option(
            "--pretty/--no-pretty",
            help="Pretty format transpiled SQL output.",
        ),
    ] = False,
) -> None:
    sql = input_path.read_text(encoding="utf-8")

    try:
        statements = transpile(sql, read=read, write=write, pretty=pretty)
    except Exception as exc:
        typer.echo(f"Transpile failed ({read} -> {write}): {exc}", err=True)
        raise typer.Exit(code=1) from exc

    output_sql = _serialize_statements(statements)
    if not output_sql:
        typer.echo("Transpile produced empty output.", err=True)
        raise typer.Exit(code=1)

    input_path.write_text(output_sql, encoding="utf-8")


def main() -> None:
    app()
