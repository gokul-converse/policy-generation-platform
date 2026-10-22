
import asyncio
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, insert, select

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import AsyncSessionLocal


REFERENCE_DATA = {
    "leave_types": [
        {
            "name": "Annual Leave",
            "description": "Annual paid leave",
        },
        {
            "name": "Sick Leave",
            "description": "Leave for illness",
        },
        {
            "name": "Casual Leave",
            "description": "Short personal leave",
        },
        {
            "name": "Maternity Leave",
            "description": "Maternity-related leave",
        },
    ],
    "expense_categories": [
        {
            "name": "Travel",
            "description": "Business travel expenses",
        },
        {
            "name": "Meals",
            "description": "Business meal expenses",
        },
        {
            "name": "Accommodation",
            "description": "Business lodging expenses",
        },
        {
            "name": "Office Supplies",
            "description": "Work-related supplies",
        },
    ],
    "access_roles": [
        {
            "role_name": "Employee",
            "description": "Standard employee access",
        },
        {
            "role_name": "Manager",
            "description": "Team management access",
        },
        {
            "role_name": "HR",
            "description": "Human resources access",
        },
        {
            "role_name": "Admin",
            "description": "Administrative access",
        },
    ],
    "approval_rules": [
        {
            "domain": "hr",
            "rule_name": "Leave Approval",
            "condition_description": (
                "Leave requests require review before approval."
            ),
            "approver_role": "Manager",
        },
        {
            "domain": "finance",
            "rule_name": "Expense Approval",
            "condition_description": (
                "Expense claims require review before approval."
            ),
            "approver_role": "Manager",
        },
        {
            "domain": "it_security",
            "rule_name": "Access Approval",
            "condition_description": (
                "Access requests require authorization before granting access."
            ),
            "approver_role": "Admin",
        },
        {
            "domain": "general",
            "rule_name": "Policy Approval",
            "condition_description": (
                "Policy changes require review before publication."
            ),
            "approver_role": "HR",
        },
    ],
}


def make_row(table, item):
    """Map seed values to existing table columns and validate required fields."""
    columns = {column.name for column in table.columns}
    row = {}

    # Copy only fields that exist in the database table.
    for key, value in item.items():
        if key in columns:
            row[key] = value

    # Reference data is illustrative, not company-verified.
    if "data_status" in columns:
        row["data_status"] = "sample"

    # Validate mandatory columns before attempting the INSERT.
    for column in table.columns:
        if (
            column.name not in row
            and not column.primary_key
            and not column.nullable
            and column.default is None
            and column.server_default is None
            and column.autoincrement is not True
        ):
            return None, f"Required column needs a value: {column.name}"

    return row, None


def get_name_column(table):
    """Return the appropriate name column for duplicate detection."""
    columns = {column.name for column in table.columns}

    for name in (
        "name",
        "type_name",
        "category_name",
        "role_name",
        "rule_name",
        "display_name",
    ):
        if name in columns:
            return name

    return None


async def main():
    async with AsyncSessionLocal() as session:
        try:
            connection = await session.connection()
            metadata = MetaData()

            await connection.run_sync(
                lambda sync_connection: metadata.reflect(
                    bind=sync_connection,
                    only=list(REFERENCE_DATA.keys()),
                )
            )

            total_inserted = 0

            for table_name, items in REFERENCE_DATA.items():
                table = metadata.tables.get(table_name)

                if table is None:
                    print(f"SKIPPED {table_name}: table not found")
                    continue

                inserted_count = 0
                skipped_count = 0
                name_column = get_name_column(table)

                for item in items:
                    row, error = make_row(table, item)

                    item_label = (
                        item.get("name")
                        or item.get("role_name")
                        or item.get("rule_name")
                        or "unknown"
                    )

                    if error:
                        print(
                            f"SKIPPED {table_name}/{item_label}: {error}"
                        )
                        skipped_count += 1
                        continue

                    # Avoid inserting an existing record.
                    if name_column and name_column in row:
                        result = await session.execute(
                            select(table.c[name_column])
                            .where(
                                table.c[name_column] == row[name_column]
                            )
                            .limit(1)
                        )

                        if result.first():
                            print(
                                f"EXISTS {table_name}/{item_label}"
                            )
                            continue

                    await session.execute(
                        insert(table).values(**row)
                    )

                    inserted_count += 1
                    total_inserted += 1

                print(
                    f"{table_name}: inserted {inserted_count}, "
                    f"skipped {skipped_count}"
                )

            await session.commit()

            print("\nReference data seeding completed.")
            print(f"Total new rows inserted: {total_inserted}")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
