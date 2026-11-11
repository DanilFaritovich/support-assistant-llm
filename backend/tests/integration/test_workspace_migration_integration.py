import os
import sqlite3
import subprocess
from pathlib import Path


def test_workspace_migration_upgrades_and_downgrades_existing_database(
    tmp_path: Path,
) -> None:
    backend = Path(__file__).resolve().parents[2]
    database = tmp_path / "migration.db"
    env = os.environ | {"DATABASE_URL": f"sqlite+aiosqlite:///{database}"}

    def migrate(*args: str) -> None:
        import sys

        subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    migrate("upgrade", "6875848d7404")
    with sqlite3.connect(database) as connection:
        previous = connection.execute(
            "SELECT id, name FROM departments ORDER BY id"
        ).fetchall()
    migrate("upgrade", "head")
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT count(*) FROM guest_workspaces"
        ).fetchone() == (0,)
        assert (
            connection.execute(
                "SELECT id, name FROM departments ORDER BY id"
            ).fetchall()
            == previous
        )
        assert connection.execute("PRAGMA index_list(guest_workspaces)").fetchall()
    migrate("downgrade", "6875848d7404")
    with sqlite3.connect(database) as connection:
        assert not connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'guest_workspaces'"
        ).fetchall()
        assert (
            connection.execute(
                "SELECT id, name FROM departments ORDER BY id"
            ).fetchall()
            == previous
        )
