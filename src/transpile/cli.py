from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff
from fnmatch import fnmatch
from pathlib import Path
from typing import Annotated

import typer
from polyglot_sql import transpile

app = typer.Typer(no_args_is_help=True)

DEFAULT_INCLUDE_PATTERNS = ("*.sql",)
DEFAULT_SKIP_DIRS = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
})


@dataclass(slots=True)
class RunStats:
    scanned: int = 0
    changed: int = 0
    unchanged: int = 0
    failed: int = 0


def _normalize_patterns(patterns: list[str] | None) -> tuple[str, ...]:
    if patterns is None:
        return DEFAULT_INCLUDE_PATTERNS
    cleaned = tuple(pattern.strip() for pattern in patterns if pattern.strip())
    return cleaned or DEFAULT_INCLUDE_PATTERNS


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    basename = path.rsplit("/", 1)[-1]
    for pattern in patterns:
        if fnmatch(path, pattern):
            return True
        # Treat simple filename patterns as depth-agnostic for better ergonomics.
        if "/" not in pattern and fnmatch(basename, pattern):
            return True
    return False


def _should_process(
    relative_path: str,
    *,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> bool:
    if not _matches(relative_path, include_patterns):
        return False
    if exclude_patterns and _matches(relative_path, exclude_patterns):
        return False
    return True


def _candidate_files(
    target: Path,
    *,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> list[Path]:
    if target.is_file():
        return [target]

    files: list[Path] = []

    walker = target.walk(top_down=True)
    for root, dirnames, filenames in walker:
        dirnames[:] = [dirname for dirname in dirnames if dirname not in DEFAULT_SKIP_DIRS]
        for filename in filenames:
            path = root / filename
            rel = path.relative_to(target).as_posix()
            if not _should_process(
                rel,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            ):
                continue
            files.append(path)

    files.sort()
    return files


def _transpile_content(sql: str, *, read: str, write: str, pretty: bool) -> str:
    statements = transpile(sql, read=read, write=write, pretty=pretty)
    return ";\n".join(statements)


def _print_diff(path: Path, before: str, after: str) -> None:
    diff = unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    output = "".join(diff)
    if output:
        typer.echo(output)


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
    include: Annotated[
        list[str] | None,
        typer.Option(
            help="Glob(s) to include. Repeat option for multiple patterns.",
        ),
    ] = None,
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
) -> None:
    include_patterns = _normalize_patterns(include)
    exclude_patterns = tuple(exclude or ())
    files = _candidate_files(
        target,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )

    stats = RunStats(scanned=len(files))

    if not files:
        typer.echo("No matching files found.")
        raise typer.Exit(code=0)

    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            output = _transpile_content(source, read=read, write=write, pretty=pretty)
        except Exception as exc:
            stats.failed += 1
            typer.echo(f"FAIL {path}: {exc}", err=True)
            continue

        if output == source:
            stats.unchanged += 1
            typer.echo(f"UNCHANGED {path}")
            continue

        stats.changed += 1
        typer.echo(f"CHANGED {path}")

        if diff:
            _print_diff(path, source, output)

        path.write_text(output, encoding="utf-8")

    typer.echo(
        (
            f"Summary: scanned={stats.scanned} "
            f"changed={stats.changed} unchanged={stats.unchanged} failed={stats.failed}"
        )
    )

    if stats.failed > 0:
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


def main() -> None:
    app()
