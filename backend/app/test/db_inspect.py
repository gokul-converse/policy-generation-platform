
"""Inspect the development SQLite database without modifying it."""

import sqlite3
from pathlib import Path

database_path = Path("data/policy_generation.db")

if not database_path.exists():
    print(f"Database file not found: {database_path.resolve()}")
else:
    with sqlite3.connect(database_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?",
            ("table",),
        ).fetchall()

        print("Tables:", [table[0] for table in tables])

        table_names = {table[0] for table in tables}

        if "skills" in table_names:
            count = connection.execute(
                "SELECT COUNT(*) FROM skills"
            ).fetchone()[0]
            print("Skills:", count)
        else:
            print("Skills table missing")

        if "skill_versions" in table_names:
            count = connection.execute(
                "SELECT COUNT(*) FROM skill_versions"
            ).fetchone()[0]
            print("Versions:", count)
        else:
            print("Skill versions table missing")

        if "alembic_version" in table_names:
            revision = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchall()
            print("Alembic revision:", revision)
        else:
            print("Alembic revision: not initialized")
