
import sqlite3
from app.db.session import DATABASE_PATH

connection = sqlite3.connect(str(DATABASE_PATH))

try:
    cursor = connection.cursor()

    print("Alembic version:")
    print(
        cursor.execute("SELECT * FROM alembic_version").fetchall()
    )

    print("\nSkills indexes:")
    indexes = cursor.execute(
        "PRAGMA index_list('skills')"
    ).fetchall()

    for index in indexes:
        print(index)

    print("\nCase-insensitive index definition:")
    result = cursor.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'index' "
        "AND name = 'uq_skills_name_lower'"
    ).fetchone()

    print(result[0] if result else "Index not found")

finally:
    connection.close()
