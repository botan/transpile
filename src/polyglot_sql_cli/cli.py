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
    return any(fnmatch(path, pattern) for pattern in patterns)


def _candidate_files(
    target: Path,
    *,
    recursive: bool,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> list[Path]:
    if target.is_file():
        return [target]

    files: list[Path] = []

    if recursive:
        walker = target.walk(top_down=True)
        for root, dirnames, filenames in walker:
            dirnames[:] = [dirname for dirname in dirnames if dirname not in DEFAULT_SKIP_DIRS]
            for filename in filenames:
                path = root / filename
                rel = path.relative_to(target).as_posix()
                if not _matches(rel, include_patterns):
                    continue
                if exclude_patterns and _matches(rel, exclude_patterns):
                    continue
                files.append(path)
    else:
        for path in target.iterdir():
            if not path.is_file():
                continue
            rel = path.relative_to(target).as_posix()
            if not _matches(rel, include_patterns):
                continue
            if exclude_patterns and _matches(rel, exclude_patterns):
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
        typer.Option("--read", "-r", help="Source SQL dialect."),
    ],
    write: Annotated[
        str,
        typer.Option("--write", "-w", help="Target SQL dialect."),
    ],
    pretty: Annotated[
        bool,
        typer.Option(help="Pretty format transpiled SQL output."),
    ] = False,
    recursive: Annotated[
        bool,
        typer.Option("--recursive/--no-recursive", help="Walk directories recursively."),
    ] = True,
    include: Annotated[
        list[str] | None,
        typer.Option(
            "--include",
            help="Glob(s) to include. Repeat option for multiple patterns.",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            help="Glob(s) to exclude. Repeat option for multiple patterns.",
        ),
    ] = None,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help="Do not write changes; fail if any file would change.",
        ),
    ] = False,
    diff: Annotated[
        bool,
        typer.Option("--diff", help="Print unified diff for changed files."),
    ] = False,
) -> None:
    include_patterns = _normalize_patterns(include)
    exclude_patterns = tuple(exclude or ())
    files = _candidate_files(
        target,
        recursive=recursive,
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

        if not check:
            path.write_text(output, encoding="utf-8")

    typer.echo(
        (
            f"Summary: scanned={stats.scanned} "
            f"changed={stats.changed} unchanged={stats.unchanged} failed={stats.failed}"
        )
    )

    if stats.failed > 0:
        raise typer.Exit(code=1)

    if check and stats.changed > 0:
        raise typer.Exit(code=2)

    raise typer.Exit(code=0)


def main() -> None:
    app()
