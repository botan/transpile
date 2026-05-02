from pathlib import Path

from typer.testing import CliRunner

import polyglot_sql_cli.cli as cli_module

runner = CliRunner()


def test_cli_overwrites_sql_file_and_passes_pretty(monkeypatch, tmp_path: Path) -> None:
    input_file = tmp_path / "query.sql"
    input_file.write_text("select 1", encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_transpile(
        sql: str,
        read: str | None = None,
        write: str | None = None,
        *,
        pretty: bool = False,
    ) -> list[str]:
        calls["sql"] = sql
        calls["read"] = read
        calls["write"] = write
        calls["pretty"] = pretty
        return ["SELECT 1  ", "", "SELECT 2;"]

    monkeypatch.setattr(cli_module, "transpile", fake_transpile)

    result = runner.invoke(
        cli_module.app,
        [str(input_file), "--read", "postgres", "--write", "snowflake", "--pretty"],
    )

    assert result.exit_code == 0
    assert input_file.read_text(encoding="utf-8") == "SELECT 1;\nSELECT 2;\n"
    assert calls == {
        "sql": "select 1",
        "read": "postgres",
        "write": "snowflake",
        "pretty": True,
    }


def test_cli_fails_for_missing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.sql"

    result = runner.invoke(
        cli_module.app,
        [str(missing_file), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 2
    assert "Invalid value for 'INPUT_PATH':" in result.output
    assert "does not exist" in result.output


def test_cli_fails_for_non_sql_file(tmp_path: Path) -> None:
    input_file = tmp_path / "query.txt"
    input_file.write_text("select 1", encoding="utf-8")

    result = runner.invoke(
        cli_module.app,
        [str(input_file), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 2
    assert "Invalid value for 'INPUT_PATH': Path must point to a .sql file." in result.output


def test_cli_fails_when_transpile_raises(monkeypatch, tmp_path: Path) -> None:
    input_file = tmp_path / "query.sql"
    input_file.write_text("select 1", encoding="utf-8")

    def fake_transpile(
        sql: str,
        read: str | None = None,
        write: str | None = None,
        *,
        pretty: bool = False,
    ) -> list[str]:
        del sql, read, write, pretty
        raise ValueError("bad dialect")

    monkeypatch.setattr(cli_module, "transpile", fake_transpile)

    result = runner.invoke(
        cli_module.app,
        [str(input_file), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 1
    assert "Transpile failed (postgres -> snowflake): bad dialect" in result.output


def test_cli_fails_on_empty_transpile_output(monkeypatch, tmp_path: Path) -> None:
    input_file = tmp_path / "query.sql"
    input_file.write_text("select 1", encoding="utf-8")

    def fake_transpile(
        sql: str,
        read: str | None = None,
        write: str | None = None,
        *,
        pretty: bool = False,
    ) -> list[str]:
        del sql, read, write, pretty
        return []

    monkeypatch.setattr(cli_module, "transpile", fake_transpile)

    result = runner.invoke(
        cli_module.app,
        [str(input_file), "--read", "postgres", "--write", "snowflake"],
    )

    assert result.exit_code == 1
    assert "Transpile produced empty output." in result.output
