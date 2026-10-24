"""Running the seed end to end: `python -m salary_api.seed` (docs/12-seed-data.md sections 13-14).

These tests write a small SQLite file under tmp_path, as `make seed` and `make seed-turso` do.
"""

import io
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import insert

from salary_api.core.db import create_engine_for_url
from salary_api.modules.reference.models import Country
from salary_api.seed.cli import main
from salary_api.seed.errors import SeedRefused
from salary_api.seed.loader import ALEMBIC_INI
from salary_api.seed.runner import SeedOptions, run_seed
from tests.factories import FAST_PASSWORD_HASHER, make_seed_settings

# Low entropy on purpose, so secret scanners (gitleaks) do not mistake them for real ones.
REAL_PASSWORDS = {
    "seed_admin_password": "admin" + "x" * 16,
    "seed_hr_password": "hr" + "y" * 16,
    "seed_viewer_password": "viewer" + "z" * 16,
}


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def _run(path: Path, *, app_env: str = "test", **options: object) -> str:
    out = io.StringIO()
    settings = make_seed_settings(app_env=app_env, **REAL_PASSWORDS)
    defaults: dict[str, object] = {"seed": 42, "employees": 40, "db_url": _url(path)}
    run_seed(
        SeedOptions(**(defaults | options)),  # type: ignore[arg-type]
        settings,
        hasher=FAST_PASSWORD_HASHER,
        out=out,
    )
    return out.getvalue()


def _count(path: Path, table: str) -> int:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # noqa: S608


def test_the_seed_migrates_an_empty_file_and_fills_it(tmp_path: Path) -> None:
    database = tmp_path / "seed.db"

    _run(database)

    assert _count(database, "employees") == 40
    assert _count(database, "users") == 3
    with closing(sqlite3.connect(database)) as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version is not None


def test_the_seed_file_is_one_self_contained_file(tmp_path: Path) -> None:
    database = tmp_path / "seed.db"

    _run(database)

    wal = tmp_path / "seed.db-wal"
    assert not wal.exists() or wal.stat().st_size == 0
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_the_summary_shows_counts_per_country_department_level_and_type_and_timings(
    tmp_path: Path,
) -> None:
    summary = _run(tmp_path / "seed.db", employees=200)

    assert "200 employees" in summary
    assert "US 60" in summary
    assert re.search(r"Engineering \d+  Sales \d+", summary)
    assert re.search(r"L1 \d+", summary)
    assert "FULL_TIME 180" in summary
    assert re.search(r"salary records\s+[\d,]+", summary)
    assert re.search(r"components\s+[\d,]+", summary)
    assert re.search(r"generate\s+[\d.]+ s", summary)
    assert re.search(r"total\s+[\d.]+ s", summary)


def test_a_turso_token_in_the_environment_does_not_break_a_local_file(tmp_path: Path) -> None:
    database = tmp_path / "seed.db"
    settings = make_seed_settings(database_auth_token="token-" + "t" * 16, **REAL_PASSWORDS)

    run_seed(
        SeedOptions(employees=10, db_url=_url(database)),
        settings,
        hasher=FAST_PASSWORD_HASHER,
        out=io.StringIO(),
    )

    assert _count(database, "employees") == 10


def test_running_twice_needs_reset_and_reset_gives_the_same_counts(tmp_path: Path) -> None:
    database = tmp_path / "seed.db"
    _run(database)

    with pytest.raises(SeedRefused, match="--reset"):
        _run(database)
    _run(database, reset=True)

    assert _count(database, "employees") == 40


def test_a_database_with_data_is_refused_before_it_is_migrated(tmp_path: Path) -> None:
    database = tmp_path / "old.db"
    engine = create_engine_for_url(_url(database))
    config = Config(ALEMBIC_INI)
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0003")
    with engine.begin() as connection:
        connection.execute(insert(Country).values(code="US", name="US", default_currency="USD"))
    engine.dispose()

    with pytest.raises(SeedRefused, match="--reset"):
        _run(database)

    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0003",)


def test_production_refuses_a_reset_unless_forced(tmp_path: Path) -> None:
    database = tmp_path / "seed.db"

    with pytest.raises(SeedRefused, match="--force-demo"):
        _run(database, app_env="production", reset=True)

    assert not database.exists()


def test_production_may_reset_demo_data_when_forced(tmp_path: Path) -> None:
    database = tmp_path / "seed.db"
    _run(database, app_env="production")

    _run(database, app_env="production", reset=True, force_demo=True)

    assert _count(database, "employees") == 40


def test_production_refuses_default_passwords_before_touching_the_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "seed.db"
    settings = make_seed_settings(app_env="production")

    with pytest.raises(SeedRefused, match="SEED_ADMIN_PASSWORD"):
        run_seed(
            SeedOptions(employees=10, db_url=_url(database)),
            settings,
            hasher=FAST_PASSWORD_HASHER,
            out=io.StringIO(),
        )

    assert not database.exists()


def test_the_command_line_seeds_the_given_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)  # no .env file here
    monkeypatch.setenv("APP_ENV", "test")
    database = tmp_path / "cli.db"

    status = main(["--seed", "7", "--employees", "25", "--no-history", "--db-url", _url(database)])

    assert status == 0
    assert _count(database, "employees") == _count(database, "salary_records") == 25
    assert "25 employees" in capsys.readouterr().out


def test_the_command_line_reports_a_refusal_and_exits_with_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "production")
    for variable in ("SEED_ADMIN_PASSWORD", "SEED_HR_PASSWORD", "SEED_VIEWER_PASSWORD"):
        monkeypatch.delenv(variable, raising=False)

    status = main(["--employees", "5", "--db-url", _url(tmp_path / "x.db")])

    assert status == 2
    assert "SEED_ADMIN_PASSWORD is not set" in capsys.readouterr().err
