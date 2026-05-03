from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import polyglot_sql_cli.cli as cli_module

runner = CliRunner()


def test_cli_transpiles_single_file_in_place(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "query.sql"
    target.write_text("select 1", encoding="utf-8")

    def fake_transpile(
        sql: str,
        read: str | None = None,
        write: str | None = None,
        *,
        pretty: bool = False,
    ) -> list[str]:
        assert sql == "select 1"
        assert read == "postgres"
        assert write == "snowflake"
        assert pretty is True
        return ["SELECT 1"]

    monkeypatch.setattr(cli_module, "transpile", fake_transpile)

    result = runner.invoke(
        cli_module.app,
        [str(target), "--read", "postgres", "--write", "snowflake", "--pretty"],
    )

    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") == "SELECT 1"
    assert "Summary: scanned=1 changed=1 unchanged=0 failed=0" in result.stdout


def test_cli_transpiles_directory_recursively(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "sql"
    nested = root / "nested"
    root.mkdir()
    nested.mkdir()

    first = root / "a.sql"
    second = nested / "b.sql"
    non_sql = nested / "note.txt"

    first.write_text("select 1", encoding="utf-8")
    second.write_text("select 2", encoding="utf-8")
    non_sql.write_text("skip", encoding="utf-8")

    def fake_transpile(
        sql: str,
        read: str | None = None,
        write: str | None = None,
        *,
        pretty: bool = False,
    ) -> list[str]:
        del read, write, pretty
        return [sql.upper()]

    monkeypatch.setattr(cli_module, "transpile", fake_transpile)

    result = runner.invoke(
        cli_module.app,
        [str(root), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 0
    assert first.read_text(encoding="utf-8") == "SELECT 1"
    assert second.read_text(encoding="utf-8") == "SELECT 2"
    assert non_sql.read_text(encoding="utf-8") == "skip"
    assert "Summary: scanned=2 changed=2 unchanged=0 failed=0" in result.stdout


def test_cli_no_recursive_only_processes_top_level(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "sql"
    nested = root / "nested"
    root.mkdir()
    nested.mkdir()

    top_file = root / "a.sql"
    nested_file = nested / "b.sql"

    top_file.write_text("select 1", encoding="utf-8")
    nested_file.write_text("select 2", encoding="utf-8")

    monkeypatch.setattr(
        cli_module,
        "transpile",
        lambda sql, read=None, write=None, *, pretty=False: [sql.upper()],
    )

    result = runner.invoke(
        cli_module.app,
        [
            str(root),
            "--read",
            "postgres",
            "--write",
            "snowflake",
            "--no-recursive",
        ],
    )

    assert result.exit_code == 0
    assert top_file.read_text(encoding="utf-8") == "SELECT 1"
    assert nested_file.read_text(encoding="utf-8") == "select 2"
    assert "Summary: scanned=1 changed=1 unchanged=0 failed=0" in result.stdout


def test_cli_respects_exclude_and_polyglotignore(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "sql"
    root.mkdir()

    keep = root / "keep.sql"
    excluded = root / "skip.sql"
    ignored = root / "ignore_me.sql"
    ignore_file = root / ".polyglotignore"

    keep.write_text("select 1", encoding="utf-8")
    excluded.write_text("select 2", encoding="utf-8")
    ignored.write_text("select 3", encoding="utf-8")
    ignore_file.write_text("ignore_me.sql\n", encoding="utf-8")

    monkeypatch.setattr(
        cli_module,
        "transpile",
        lambda sql, read=None, write=None, *, pretty=False: [sql.upper()],
    )

    result = runner.invoke(
        cli_module.app,
        [
            str(root),
            "--read",
            "postgres",
            "--write",
            "snowflake",
            "--exclude",
            "skip.sql",
        ],
    )

    assert result.exit_code == 0
    assert keep.read_text(encoding="utf-8") == "SELECT 1"
    assert excluded.read_text(encoding="utf-8") == "select 2"
    assert ignored.read_text(encoding="utf-8") == "select 3"
    assert "Summary: scanned=1 changed=1 unchanged=0 failed=0" in result.stdout


def test_cli_check_mode_does_not_write_and_returns_two_on_changes(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "query.sql"
    target.write_text("select 1", encoding="utf-8")

    monkeypatch.setattr(
        cli_module,
        "transpile",
        lambda sql, read=None, write=None, *, pretty=False: [sql.upper()],
    )

    result = runner.invoke(
        cli_module.app,
        [str(target), "--read", "postgres", "--write", "snowflake", "--check"],
    )

    assert result.exit_code == 2
    assert target.read_text(encoding="utf-8") == "select 1"
    assert "Summary: scanned=1 changed=1 unchanged=0 failed=0" in result.stdout


def test_cli_diff_prints_patch(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "query.sql"
    target.write_text("select 1\n", encoding="utf-8")

    monkeypatch.setattr(
        cli_module,
        "transpile",
        lambda sql, read=None, write=None, *, pretty=False: [sql.upper()],
    )

    result = runner.invoke(
        cli_module.app,
        [str(target), "--read", "postgres", "--write", "snowflake", "--diff"],
    )

    assert result.exit_code == 0
    assert "--- a/" in result.stdout
    assert "+++ b/" in result.stdout
    assert "-select 1" in result.stdout
    assert "+SELECT 1" in result.stdout


def test_cli_continues_on_errors_and_returns_one(monkeypatch, tmp_path: Path) -> None:
    first = tmp_path / "a.sql"
    second = tmp_path / "b.sql"

    first.write_text("ok", encoding="utf-8")
    second.write_text("boom", encoding="utf-8")

    def fake_transpile(
        sql: str,
        read: str | None = None,
        write: str | None = None,
        *,
        pretty: bool = False,
    ) -> list[str]:
        del read, write, pretty
        if sql == "boom":
            raise ValueError("bad sql")
        return ["OK"]

    monkeypatch.setattr(cli_module, "transpile", fake_transpile)

    result = runner.invoke(
        cli_module.app,
        [str(tmp_path), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 1
    assert first.read_text(encoding="utf-8") == "OK"
    assert second.read_text(encoding="utf-8") == "boom"
    assert "Summary: scanned=2 changed=1 unchanged=0 failed=1" in result.stdout


def test_cli_fails_for_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    result = runner.invoke(
        cli_module.app,
        [str(missing_path), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 2
    assert "Invalid value for 'TARGET':" in result.output
