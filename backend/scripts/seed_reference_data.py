
"""Seed synthetic reference data for the policy-generation POC.

Safe to rerun: existing reference records are not duplicated.
Run from backend: python scripts/seed_reference_data.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure the backend directory is importable when run as a script.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import (
    AccessRole,
    ApprovalRule,
    ExpenseCategory,
    LeaveType,
)


LEAVE_TYPES = [
    {
        "name": "Annual Leave",
        "annual_limit": 18,
        "description": "Sample annual leave allowance from the POC policy.",
    },
    {
        "name": "Sick Leave",
        "annual_limit": 12,
        "description": "Sample leave category for illness or medical needs.",
    },
    {
        "name": "Casual Leave",
        "annual_limit": 6,
        "description": "Sample leave category for personal matters.",
    },
    {
        "name": "Maternity Leave",
        "annual_limit": None,
        "description": "Sample maternity leave category; entitlement requires policy verification.",
    },
]

EXPENSE_CATEGORIES = [
    {
        "name": "Travel",
        "description": "Sample business travel expenses.",
    },
    {
        "name": "Meals",
        "description": "Sample meals and food expenses during business activities.",
    },
    {
        "name": "Accommodation",
        "description": "Sample hotel and business accommodation expenses.",
    },
    {
        "name": "Internet",
        "description": "Sample business internet and connectivity expenses.",
    },
]

ACCESS_ROLES = [
    {
        "role_name": "Employee",
        "description": "Sample role for submitting requests and expenses.",
    },
    {
        "role_name": "Manager",
        "description": "Sample role for reviewing team requests.",
    },
    {
        "role_name": "HR",
        "description": "Sample role for HR policy and leave administration.",
    },
    {
        "role_name": "Finance",
        "description": "Sample role for expense review and finance operations.",
    },
]

APPROVAL_RULES = [
    {
        "domain": "hr",
        "rule_name": "Leave Request Review",
        "condition_description": (
            "Sample rule: a leave request requires manager review."
        ),
        "approver_role": "Manager",
    },
    {
        "domain": "finance",
        "rule_name": "Expense Claim Review",
        "condition_description": (
            "Sample rule: an expense claim requires finance review."
        ),
        "approver_role": "Finance",
    },
    {
        "domain": "finance",
        "rule_name": "High Value Expense Review",
        "condition_description": (
            "Sample rule: a high-value expense requires manager and finance review."
        ),
        "approver_role": "Manager, Finance",
    },
    {
        "domain": "it_security",
        "rule_name": "Access Request Review",
        "condition_description": (
            "Sample rule: access requests require authorization before access is granted."
        ),
        "approver_role": "Manager",
    },
]


async def seed_reference_data() -> None:
    async with AsyncSessionLocal() as session:
        added = {
            "leave_types": 0,
            "expense_categories": 0,
            "access_roles": 0,
            "approval_rules": 0,
        }

        try:
            # Leave types: name is unique.
            for item in LEAVE_TYPES:
                existing = await session.scalar(
                    select(LeaveType).where(LeaveType.name == item["name"])
                )
                if existing is None:
                    session.add(LeaveType(**item, data_status="sample"))
                    added["leave_types"] += 1

            # Expense categories: name is unique.
            for item in EXPENSE_CATEGORIES:
                existing = await session.scalar(
                    select(ExpenseCategory).where(
                        ExpenseCategory.name == item["name"]
                    )
                )
                if existing is None:
                    session.add(ExpenseCategory(**item, data_status="sample"))
                    added["expense_categories"] += 1

            # Access roles: role_name is unique.
            for item in ACCESS_ROLES:
                existing = await session.scalar(
                    select(AccessRole).where(
                        AccessRole.role_name == item["role_name"]
                    )
                )
                if existing is None:
                    session.add(AccessRole(**item, data_status="sample"))
                    added["access_roles"] += 1

            # ApprovalRule has no unique constraint in the current model.
            # Check domain + rule_name to avoid inserting duplicates.
            for item in APPROVAL_RULES:
                existing = await session.scalar(
                    select(ApprovalRule).where(
                        ApprovalRule.domain == item["domain"],
                        ApprovalRule.rule_name == item["rule_name"],
                    )
                )
                if existing is None:
                    session.add(ApprovalRule(**item, data_status="sample"))
                    added["approval_rules"] += 1

            await session.commit()

            print("\nSynthetic reference data seeding completed.")
            for table_name, count in added.items():
                print(f"  {table_name}: {count} new record(s)")

            print("\nAll inserted records are marked data_status='sample'.")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_reference_data())
