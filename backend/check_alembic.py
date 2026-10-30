
import sqlite3
from app.db.session import DATABASE_PATH

connection = sqlite3.connect(str(DATABASE_PATH))

try:
    cursor = connection.cursor()

    print("Database:", DATABASE_PATH)

    tables = cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' ORDER BY name"
    ).fetchall()

    print("\nTables:")
    for (table_name,) in tables:
        print("-", table_name)

    version_exists = cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='alembic_version'"
    ).fetchone()

    print("\nAlembic version:")
    if version_exists:
        print(cursor.execute("SELECT * FROM alembic_version").fetchall())
    else:
        print("alembic_version table does not exist")

    for table_name in (
        "requirement_sessions",
        "documents",
        "approval_rules",
    ):
        schema = cursor.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()

        print(f"\n{table_name} schema:")
        print(schema[0] if schema else "Table does not exist")

finally:
    connection.close()
