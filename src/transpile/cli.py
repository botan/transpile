from dataclasses import dataclass
from difflib import unified_diff
from fnmatch import fnmatch
from pathlib import Path
from typing import Annotated

import typer
from polyglot_sql import dialects as available_dialects
from polyglot_sql import transpile

app = typer.Typer(no_args_is_help=True)


@dataclass(slots=True)
class RunStats:
    scanned: int = 0
    changed: int = 0
    unchanged: int = 0
    failed: int = 0


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    basename = path.rsplit("/", 1)[-1]
    return any(
        fnmatch(path, pattern)
        # Treat simple filename patterns as depth-agnostic for better ergonomics.
        or ("/" not in pattern and fnmatch(basename, pattern))
        for pattern in patterns
    )


def _should_process(
    relative_path: str,
    *,
    exclude_patterns: tuple[str, ...],
) -> bool:
    return _matches(relative_path, ("*.sql",)) and not (
        exclude_patterns and _matches(relative_path, exclude_patterns)
    )


def _candidate_files(
    target: Path,
    *,
    exclude_patterns: tuple[str, ...],
) -> list[Path]:
    if target.is_file():
        return [target]

    files = [
        path
        for root, _dirnames, filenames in target.walk(top_down=True)
        for filename in filenames
        if _should_process(
            (path := root / filename).relative_to(target).as_posix(),
            exclude_patterns=exclude_patterns,
        )
    ]
    return sorted(files)


def _transpile_content(sql: str, *, read: str, write: str, pretty: bool) -> str:
    return ";\n".join(transpile(sql, read=read, write=write, pretty=pretty))


def _print_diff(path: Path, before: str, after: str) -> None:
    if output := "".join(
        unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    ):
        typer.echo(output)


def _acceptable_dialects() -> tuple[str, ...]:
    return tuple(sorted(available_dialects()))


def _show_dialects_and_exit(value: bool) -> bool:
    if value:
        typer.echo("\n".join(_acceptable_dialects()))
        raise typer.Exit(code=0)
    return value


@app.command()
def cli(
    target: Annotated[
        Path,
        typer.Argument(
            help="Path to a SQL file or directory.",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    read: Annotated[
        str,
        typer.Option(help="Source SQL dialect."),
    ],
    write: Annotated[
        str,
        typer.Option(help="Target SQL dialect."),
    ],
    pretty: Annotated[
        bool,
        typer.Option(help="Pretty format transpiled SQL output."),
    ] = False,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            help="Glob(s) to exclude. Repeat option for multiple patterns.",
        ),
    ] = None,
    diff: Annotated[
        bool,
        typer.Option(help="Print unified diff for changed files."),
    ] = False,
    dialects: Annotated[
        bool,
        typer.Option(
            help="Print all acceptable SQL dialect names and exit.",
            callback=_show_dialects_and_exit,
            is_eager=True,
        ),
    ] = False,
) -> None:
    del dialects
    exclude_patterns = tuple(exclude or ())
    files = _candidate_files(target, exclude_patterns=exclude_patterns)

    stats = RunStats(scanned=len(files))

    if not files:
        typer.echo("info: no matching files found")
        raise typer.Exit(code=0)

    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            output = _transpile_content(source, read=read, write=write, pretty=pretty)
        except Exception as exc:
            stats.failed += 1
            typer.echo(f"error: {path} - {exc}", err=True)
            continue

        if output == source:
            stats.unchanged += 1
            typer.echo(f"info: unchanged {path}")
            continue

        stats.changed += 1
        typer.echo(f"info: changed {path}")

        if diff:
            _print_diff(path, source, output)

        path.write_text(output, encoding="utf-8")

    typer.echo(
        (
            f"info: summary scanned={stats.scanned} "
            f"changed={stats.changed} unchanged={stats.unchanged} failed={stats.failed}"
        )
    )

    raise typer.Exit(code=int(stats.failed > 0))


def main() -> None:
    app()
