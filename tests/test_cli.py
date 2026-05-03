from pathlib import Path

from typer.testing import CliRunner

import transpile.cli as cli_module

runner = CliRunner()


def test_cli_dialects_option_prints_acceptable_dialects(monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "available_dialects", lambda: ["snowflake", "postgres"])

    result = runner.invoke(cli_module.app, ["--dialects"])

    assert result.exit_code == 0
    assert result.stdout == "postgres\nsnowflake\n"


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
    assert "info: summary scanned=1 changed=1 unchanged=0 failed=0" in result.stdout


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
    assert "info: summary scanned=2 changed=2 unchanged=0 failed=0" in result.stdout


def test_cli_respects_exclude(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "sql"
    root.mkdir()

    keep = root / "keep.sql"
    excluded = root / "skip.sql"
    included = root / "include_me.sql"

    keep.write_text("select 1", encoding="utf-8")
    excluded.write_text("select 2", encoding="utf-8")
    included.write_text("select 3", encoding="utf-8")

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
    assert included.read_text(encoding="utf-8") == "SELECT 3"
    assert "info: summary scanned=2 changed=2 unchanged=0 failed=0" in result.stdout


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
    assert "info: summary scanned=2 changed=1 unchanged=0 failed=1" in result.stdout


def test_cli_fails_for_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    result = runner.invoke(
        cli_module.app,
        [str(missing_path), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 2
    assert "Invalid value for 'TARGET':" in result.output


def test_cli_exclude_simple_name_matches_nested_paths(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "sql"
    nested = root / "nested"
    root.mkdir()
    nested.mkdir()

    keep = root / "keep.sql"
    excluded_nested = nested / "skip.sql"

    keep.write_text("select 1", encoding="utf-8")
    excluded_nested.write_text("select 2", encoding="utf-8")

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
    assert excluded_nested.read_text(encoding="utf-8") == "select 2"
    assert "info: summary scanned=1 changed=1 unchanged=0 failed=0" in result.stdout
