"""Populate PostgreSQL with sample policy documents and reference data."""

from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF
from app.db.session import engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DOCUMENT_DIR = DATA_DIR / "sample_documents"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Domains are metadata, not an allowlist. Any non-empty domain label is accepted.

SAMPLE_POLICIES = {
    "sample_hr_policy.txt": {
        "domain": "hr",
        "content": """
1. EMPLOYEE ELIGIBILITY

Employees must meet the eligibility requirements established by HR.
Employment categories and probation rules require company confirmation.

2. LEAVE MANAGEMENT

Employees should submit leave requests through the approved process.
Managers review requests and HR maintains leave records.
Leave entitlement and carry-forward rules require confirmation.

3. ATTENDANCE AND WORKING HOURS

Employees should follow their assigned working schedules.
Absences, late arrivals, and permission requests should be recorded.

4. EMPLOYEE RESPONSIBILITIES

Employees should provide accurate information and follow company policies.

5. HR RESPONSIBILITIES

HR maintains employee records and communicates policy updates.

6. POLICY REVIEW

This is sample data for testing only. Actual company rules require confirmation.
""",
    },
    "sample_finance_policy.txt": {
        "domain": "finance",
        "content": """
1. EXPENSE ELIGIBILITY

Expenses must relate to authorized business activities.

2. EXPENSE CLAIM SUBMISSION

Claims should include the amount, date, business purpose, and receipts.

3. APPROVAL WORKFLOW

Managers review business purpose and budget availability.
Finance checks supporting documents before processing claims.

4. REIMBURSEMENT

Approved claims are processed according to the company payment schedule.

5. BUDGET CONTROL

Departments should monitor spending against approved budgets.

6. FINANCE RECORDKEEPING

Finance maintains expense records and approval history.

7. POLICY REVIEW

This is sample data. Actual approval limits and timelines require confirmation.
""",
    },
    "sample_it_security_policy.txt": {
        "domain": "it_security",
        "content": """
1. USER ACCESS MANAGEMENT

System access should be granted according to job responsibilities.

2. AUTHENTICATION AND PASSWORDS

Users must protect credentials and must not share passwords or tokens.

3. DATA CLASSIFICATION

Company information should be handled according to its sensitivity.

4. SECURITY INCIDENT REPORTING

Users should report suspected phishing, data loss, and unauthorized access.

5. ACCESS REVIEW

System owners should periodically review user permissions.

6. BACKUP AND RECOVERY

Critical business data should be backed up under approved procedures.

7. POLICY REVIEW

This is sample data. Actual security requirements require confirmation.
""",
    },
    "sample_general_policy.txt": {
        "domain": "general",
        "content": """
1. PURPOSE AND SCOPE

This policy describes general company operating practices.

2. COMMUNICATION

Employees should use approved channels for business communication.

3. DOCUMENT MANAGEMENT

Business documents should be stored in approved locations.

4. RECORDKEEPING

Relevant business decisions and activities should be documented.

5. RESPONSIBILITIES

Employees follow procedures and managers communicate expectations.

6. EXCEPTIONS AND ESCALATION

Exceptions should be documented and referred to the appropriate approver.

7. POLICY REVIEW

This is sample data. Company-specific rules require confirmation.
""",
    },
}


# ---------------------------------------------------------------------------
# REFERENCE / DUMMY DATA
# ---------------------------------------------------------------------------

# annual_limit is populated because it is part of the current leave_types schema.
# Values are approved for local development/testing only; they are not
# production policy.
LEAVE_TYPES = [
    ("Casual Leave", 12, "Sample casual leave category"),
    ("Sick Leave", 12, "Sample sick leave category"),
    ("Earned Leave", 15, "Sample earned leave category"),
    ("Maternity Leave", 180, "Sample maternity leave category"),
    ("Paternity Leave", 10, "Sample paternity leave category"),
    ("Optional Holiday", 2, "Sample optional holiday category"),
]

EXPENSE_CATEGORIES = [
    ("Travel", "Business travel expenses"),
    ("Food", "Eligible business meal expenses"),
    ("Accommodation", "Business accommodation expenses"),
    ("Office Supplies", "Office stationery and supplies"),
    ("Internet", "Eligible internet and connectivity expenses"),
]

ACCESS_ROLES = [
    ("Employee", "Standard employee access"),
    ("Manager", "Team review and approval responsibilities"),
    ("HR", "Human resources administration"),
    ("Finance", "Finance review and processing"),
    ("IT Administrator", "IT system administration"),
    ("Security Administrator", "Security and access administration"),
]

APPROVAL_RULES = [
    (
        "hr",
        "Leave Request Review",
        "Review leave requests against confirmed company policy",
        "Manager",
    ),
    (
        "hr",
        "HR Policy Review",
        "Review employee policy and eligibility requirements",
        "HR",
    ),
    (
        "finance",
        "Expense Claim Review",
        "Review supporting receipts and business purpose",
        "Finance",
    ),
    (
        "finance",
        "Budget Approval",
        "Confirm budget availability before spending approval",
        "Finance Manager",
    ),
    (
        "it_security",
        "Access Request Approval",
        "Verify business need before granting system access",
        "System Owner",
    ),
    (
        "it_security",
        "Security Incident Review",
        "Review and escalate reported security incidents",
        "Security Administrator",
    ),
    (
        "general",
        "General Policy Exception",
        "Review documented exceptions to company procedures",
        "Department Manager",
    ),
]


# ---------------------------------------------------------------------------
# SAMPLE FILE CREATION
# ---------------------------------------------------------------------------

def create_sample_files() -> None:
    """Create the sample .txt policy files if they do not already exist."""
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    for filename, data in SAMPLE_POLICIES.items():
        path = DOCUMENT_DIR / filename

        # Never overwrite an existing sample file that may have been edited.
        if path.exists():
            print(f"Keeping existing sample file: {filename}")
            continue

        content = (
            "Document Status: Sample - Not Approved\n"
            f"Domain: {data['domain']}\n\n"
            f"{data['content'].strip()}\n"
        )
        path.write_text(content, encoding="utf-8")
        print(f"Created: {filename}")


# ---------------------------------------------------------------------------
# SECTION TITLE EXTRACTION
# ---------------------------------------------------------------------------

def is_heading(line: str) -> bool:
    line = line.strip()

    if not line or len(line) > 140:
        return False

    # Markdown headings.
    if re.match(r"^#{1,6}\s+\S+", line):
        return True

    # Numbered headings: 1. Heading, 1.2 Heading, 1.2.3 Heading.
    if re.match(r"^\d+(?:\.\d+)*[.)]?\s+[A-Z].{2,120}$", line):
        return True

    # "Chapter 1", "Section 2.1"
    if re.match(r"^(chapter|section)\s+\d+(?:\.\d+)*\b", line, re.IGNORECASE):
        return True

    # Mostly upper-case lines that do not look like sentences.
    letters = [char for char in line if char.isalpha()]
    if (
        len(line) >= 4
        and letters
        and sum(char.isupper() for char in letters) / len(letters) >= 0.85
        and not line.endswith((".", ",", ";"))
    ):
        return True

    return False


def clean_heading(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line.strip()).strip().strip("#").strip()


def extract_sections(page_text: str) -> list[tuple[str, str]]:
    """Return (section_title, section_text) pairs."""
    sections: list[tuple[str, str]] = []
    current_title = "General"
    current_lines: list[str] = []

    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if is_heading(line):
            content = "\n".join(current_lines).strip()
            if content:
                sections.append((current_title, content))
            current_title = clean_heading(line) or "General"
            current_lines = []
        else:
            current_lines.append(line)

    content = "\n".join(current_lines).strip()
    if content:
        sections.append((current_title, content))

    if not sections and page_text.strip():
        sections.append(("General", page_text.strip()))

    return sections


# ---------------------------------------------------------------------------
# DOCUMENT EXTRACTION
# ---------------------------------------------------------------------------

def extract_pages(path: Path) -> list[tuple[int | None, str]]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages: list[tuple[int | None, str]] = []
        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    pages.append((page_number, page_text))
        return pages

    if suffix == ".txt":
        content = path.read_text(encoding="utf-8-sig").strip()
        return [(None, content)] if content else []

    raise ValueError(f"Unsupported file format: {path.suffix}")


def split_text(raw_text: str) -> list[str]:
    """Split text into overlapping chunks, preferring word boundaries."""
    raw_text = re.sub(r"\s+", " ", raw_text).strip()
    if not raw_text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(raw_text):
        end = min(start + CHUNK_SIZE, len(raw_text))

        if end < len(raw_text):
            boundary = raw_text.rfind(" ", start, end)
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary

        chunk = raw_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(raw_text):
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


# ---------------------------------------------------------------------------
# DATABASE SCHEMA VALIDATION
# ---------------------------------------------------------------------------

async def validate_schema(connection: AsyncConnection) -> None:
    """Validate required tables and columns in PostgreSQL."""

    required = {
        "documents": {
            "document_id", "document_name", "domain", "version",
            "approval_status", "file_path", "ingestion_status",
        },
        "document_chunks": {
            "chunk_id", "document_id", "chunk_index", "section_title",
            "page_number", "chunk_text",
        },
        "leave_types": {
            "leave_type_id", "name", "annual_limit", "description",
            "data_status", "source_document_id",
        },
        "expense_categories": {
            "expense_category_id", "name", "description",
            "data_status", "source_document_id",
        },
        "access_roles": {
            "access_role_id", "role_name", "description",
            "data_status", "source_document_id",
        },
        "approval_rules": {
            "rule_id", "domain", "rule_name", "condition_description",
            "approver_role", "source_document_id", "data_status",
        },
    }

    for table_name, expected_columns in required.items():
        result = await connection.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
            """),
            {"table_name": table_name},
        )
        actual_columns = set(result.scalars().all())

        if not actual_columns:
            raise RuntimeError(
                f"Missing PostgreSQL table '{table_name}'. "
                "Run Alembic migrations first."
            )

        missing_columns = expected_columns - actual_columns
        if missing_columns:
            raise RuntimeError(
                f"Table '{table_name}' is missing columns: "
                f"{sorted(missing_columns)}"
            )

    print("PostgreSQL database schema validation passed.")


# ---------------------------------------------------------------------------
# DOCUMENT INGESTION
# ---------------------------------------------------------------------------

async def ingest_document(
    connection: AsyncConnection,
    path: Path,
    domain: str,
    approval_status: str,
) -> int:
    """Insert a document and its chunks, or refresh an existing version."""

    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("Document domain must be a non-empty string.")
    domain = domain.strip()

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    file_path = str(path.resolve())
    version = hashlib.sha256(path.read_bytes()).hexdigest()

    existing_result = await connection.execute(
        text("""
            SELECT document_id, version
            FROM documents
            WHERE file_path = :file_path
            ORDER BY document_id DESC
            LIMIT 1
        """),
        {"file_path": file_path},
    )
    existing = existing_result.mappings().first()

    if existing and existing["version"] == version:
        document_id = existing["document_id"]

        chunk_stats = await connection.execute(
            text("""
                SELECT
                    COUNT(*) AS total_chunks,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN section_title IS NULL
                                  OR TRIM(section_title) = ''
                                THEN 1 ELSE 0
                            END
                        ),
                        0
                    ) AS missing_titles
                FROM document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        )
        stats = chunk_stats.mappings().one()

        if stats["total_chunks"] > 0 and stats["missing_titles"] == 0:
            await connection.execute(
                text("""
                    UPDATE documents
                    SET domain = :domain,
                        approval_status = :approval_status,
                        ingestion_status = 'completed'
                    WHERE document_id = :document_id
                """),
                {
                    "domain": domain,
                    "approval_status": approval_status,
                    "document_id": document_id,
                },
            )
            print(
                f"Already ingested; refreshed metadata: {path.name} "
                f"(document_id={document_id})"
            )
            return document_id

        # Repair only this document's chunks.
        await connection.execute(
            text("""
                DELETE FROM document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        )
        await connection.execute(
            text("""
                UPDATE documents
                SET domain = :domain,
                    approval_status = :approval_status,
                    ingestion_status = 'processing'
                WHERE document_id = :document_id
            """),
            {
                "domain": domain,
                "approval_status": approval_status,
                "document_id": document_id,
            },
        )

    else:
        # Replace the previous version of this exact source file.
        if existing:
            await connection.execute(
                text("""
                    DELETE FROM documents
                    WHERE document_id = :document_id
                """),
                {"document_id": existing["document_id"]},
            )
            # document_chunks are deleted by the FK ON DELETE CASCADE.

        insert_result = await connection.execute(
            text("""
                INSERT INTO documents (
                    document_name,
                    domain,
                    version,
                    approval_status,
                    file_path,
                    ingestion_status
                )
                VALUES (
                    :document_name,
                    :domain,
                    :version,
                    :approval_status,
                    :file_path,
                    'processing'
                )
                RETURNING document_id
            """),
            {
                "document_name": path.name,
                "domain": domain,
                "version": version,
                "approval_status": approval_status,
                "file_path": file_path,
            },
        )
        document_id = insert_result.scalar_one()

    pages = extract_pages(path)
    if not pages:
        raise ValueError(
            f"No extractable text found in {path.name}. "
            "If this is a scanned PDF, OCR is required before ingestion."
        )

    chunk_index = 0
    for page_number, page_text in pages:
        for section_title, section_text in extract_sections(page_text):
            for chunk in split_text(section_text):
                await connection.execute(
                    text("""
                        INSERT INTO document_chunks (
                            document_id,
                            chunk_index,
                            section_title,
                            page_number,
                            chunk_text
                        )
                        VALUES (
                            :document_id,
                            :chunk_index,
                            :section_title,
                            :page_number,
                            :chunk_text
                        )
                    """),
                    {
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "section_title": section_title or "General",
                        "page_number": page_number,
                        "chunk_text": chunk,
                    },
                )
                chunk_index += 1

    await connection.execute(
        text("""
            UPDATE documents
            SET ingestion_status = 'completed'
            WHERE document_id = :document_id
        """),
        {"document_id": document_id},
    )

    print(
        f"Ingested: {path.name} | domain={domain} | "
        f"chunks={chunk_index} | document_id={document_id}"
    )
    return document_id


# ---------------------------------------------------------------------------
# REFERENCE DATA POPULATION
# ---------------------------------------------------------------------------

async def populate_reference_data(connection: AsyncConnection) -> None:
    """Insert or refresh seeded reference rows as verified test data.

    These records are for development/testing, not production policy.
    No source_document_id is assigned because they are seeded manually.
    """

    for name, annual_limit, description in LEAVE_TYPES:
        await connection.execute(
            text("""
                INSERT INTO leave_types (
                    name, annual_limit, description, data_status
                )
                SELECT
                    :name, :annual_limit, :description, 'verified'
                WHERE NOT EXISTS (
                    SELECT 1 FROM leave_types WHERE name = :name
                )
            """),
            {
                "name": name,
                "annual_limit": annual_limit,
                "description": description,
            },
        )
        await connection.execute(
            text("""
                UPDATE leave_types
                SET data_status = 'verified'
                WHERE name = :name
            """),
            {"name": name},
        )

    for name, description in EXPENSE_CATEGORIES:
        await connection.execute(
            text("""
                INSERT INTO expense_categories (
                    name, description, data_status
                )
                SELECT :name, :description, 'verified'
                WHERE NOT EXISTS (
                    SELECT 1 FROM expense_categories WHERE name = :name
                )
            """),
            {"name": name, "description": description},
        )
        await connection.execute(
            text("""
                UPDATE expense_categories
                SET data_status = 'verified'
                WHERE name = :name
            """),
            {"name": name},
        )

    for role_name, description in ACCESS_ROLES:
        await connection.execute(
            text("""
                INSERT INTO access_roles (
                    role_name, description, data_status
                )
                SELECT :role_name, :description, 'verified'
                WHERE NOT EXISTS (
                    SELECT 1 FROM access_roles
                    WHERE role_name = :role_name
                )
            """),
            {"role_name": role_name, "description": description},
        )
        await connection.execute(
            text("""
                UPDATE access_roles
                SET data_status = 'verified'
                WHERE role_name = :role_name
            """),
            {"role_name": role_name},
        )

    for domain, rule_name, condition, approver in APPROVAL_RULES:
        await connection.execute(
            text("""
                INSERT INTO approval_rules (
                    domain,
                    rule_name,
                    condition_description,
                    approver_role,
                    data_status
                )
                SELECT
                    :domain,
                    :rule_name,
                    :condition,
                    :approver_role,
                    'verified'
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM approval_rules
                    WHERE domain = :domain
                      AND rule_name = :rule_name
                )
            """),
            {
                "domain": domain,
                "rule_name": rule_name,
                "condition": condition,
                "approver_role": approver,
            },
        )
        await connection.execute(
            text("""
                UPDATE approval_rules
                SET data_status = 'verified'
                WHERE domain = :domain
                  AND rule_name = :rule_name
            """),
            {"domain": domain, "rule_name": rule_name},
        )

    # Preserve existing behaviour: mark every row as verified test data.
    for table_name in (
        "leave_types",
        "expense_categories",
        "access_roles",
        "approval_rules",
    ):
        await connection.execute(
            text(f"UPDATE {table_name} SET data_status = 'verified'")
        )

    print(
        "All populated reference rows marked verified "
        "for development/testing."
    )


# ---------------------------------------------------------------------------
# INGESTION REPORT
# ---------------------------------------------------------------------------

async def print_report(connection: AsyncConnection) -> None:
    print("\n========== DOCUMENT COUNTS BY DOMAIN ==========")
    result = await connection.execute(
        text("""
            SELECT domain, COUNT(*)
            FROM documents
            GROUP BY domain
            ORDER BY domain
        """)
    )
    for domain, count in result:
        print(f"{domain}: {count} document(s)")

    print("\n========== CHUNK / SECTION TITLE CHECK ==========")
    result = await connection.execute(
        text("""
            SELECT
                d.domain,
                COUNT(c.chunk_id),
                COALESCE(
                    SUM(
                        CASE
                            WHEN c.section_title IS NULL
                              OR TRIM(c.section_title) = ''
                            THEN 1 ELSE 0
                        END
                    ),
                    0
                )
            FROM documents AS d
            LEFT JOIN document_chunks AS c
                ON c.document_id = d.document_id
            GROUP BY d.domain
            ORDER BY d.domain
        """)
    )
    for domain, total, missing in result:
        print(f"{domain}: {total} chunks, {missing} missing section titles")

    print("\n========== REFERENCE TABLE COUNTS ==========")
    for table_name in (
        "leave_types",
        "expense_categories",
        "access_roles",
        "approval_rules",
    ):
        result = await connection.execute(
            text(f"""
                SELECT
                    COUNT(*),
                    COALESCE(
                        SUM(CASE WHEN data_status = 'verified' THEN 1 ELSE 0 END),
                        0
                    ),
                    COALESCE(
                        SUM(CASE WHEN source_document_id IS NOT NULL THEN 1 ELSE 0 END),
                        0
                    )
                FROM {table_name}
            """)
        )
        count, verified, linked = result.one()
        print(
            f"{table_name}: {count} row(s), "
            f"{verified} verified for testing, "
            f"{linked} linked to source documents"
        )

    print("\n========== DOCUMENT APPROVAL STATUS ==========")
    result = await connection.execute(
        text("""
            SELECT approval_status, COUNT(*)
            FROM documents
            GROUP BY approval_status
        """)
    )
    for status, count in result:
        print(f"{status}: {count} document(s)")

    print("\n========== SAMPLE CHUNKS ==========")
    result = await connection.execute(
        text("""
            SELECT
                d.document_name,
                d.domain,
                c.page_number,
                c.section_title,
                SUBSTRING(c.chunk_text FROM 1 FOR 100)
            FROM document_chunks AS c
            JOIN documents AS d
                ON d.document_id = c.document_id
            ORDER BY d.domain, d.document_name, c.chunk_index
            LIMIT 12
        """)
    )
    for name, domain, page, title, preview in result:
        print(
            f"[{domain}] {name} | page={page} | "
            f"section={title} | {preview}"
        )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

async def main() -> None:
    create_sample_files()

    # The PDF shown in sample_documents is required.
    # synthetic_company_policy.txt is an optional additional domain example.
    sources: Iterable[tuple[Path, str, str]] = [
        (DOCUMENT_DIR / "HRPolicy 1 2.pdf", "hr", "approved"),
        (DOCUMENT_DIR / "sample_hr_policy.txt", "hr", "approved"),
        (DOCUMENT_DIR / "sample_finance_policy.txt", "finance", "approved"),
        (DOCUMENT_DIR / "sample_it_security_policy.txt", "it_security", "approved"),
        (DOCUMENT_DIR / "sample_general_policy.txt", "general", "approved"),
        (DOCUMENT_DIR / "NovaTech_Company_Policy_Context.pdf", "general", "approved"),
        (
            DOCUMENT_DIR / "synthetic_company_policy.txt",
            "company_operations",
            "approved",
        ),
    ]

    # One transaction keeps document/chunk/reference-data changes consistent.
    # Any exception rolls back the entire population run.
    async with engine.begin() as connection:
        await validate_schema(connection)

        for path, domain, approval_status in sources:
            if not path.exists():
                if path.name == "HRPolicy 1 2.pdf":
                    raise FileNotFoundError(
                        f"Required source PDF not found: {path}"
                    )
                print(f"Skipping optional source (not found): {path.name}")
                continue

            await ingest_document(
                connection,
                path,
                domain,
                approval_status,
            )

        await populate_reference_data(connection)
        await print_report(connection)

    print("\nPostgreSQL population and ingestion completed.")


if __name__ == "__main__":
    asyncio.run(main())