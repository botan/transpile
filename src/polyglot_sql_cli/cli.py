from pathlib import Path
from typing import Annotated

import typer
from polyglot_sql import transpile

app = typer.Typer()

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
    statements = transpile(sql, read=read, write=write, pretty=pretty)
    output_sql = ";\n".join(statements)
    input_path.write_text(output_sql, encoding="utf-8")


def main() -> None:
    app()
