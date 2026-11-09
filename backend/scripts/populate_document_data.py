from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DOCUMENT_DIR = DATA_DIR / "sample_documents"
DB_PATH = DATA_DIR / "enterprise_policy.db"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Domains are metadata, not an allowlist. Any non-empty domain label is accepted.


# ---------------------------------------------------------------------------
# SAMPLE POLICY CONTENT
# ---------------------------------------------------------------------------

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
# Values are approved for local development/testing only; they are not production policy.
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

    if re.match(r"^#{1,6}\s+\S+", line):
        return True

    # Numbered headings: 1. Heading, 1.2 Heading, 1.2.3 Heading.
    if re.match(r"^\d+(?:\.\d+)*[.)]?\s+[A-Z].{2,120}$", line):
        return True

    if re.match(r"^(chapter|section)\s+\d+(?:\.\d+)*\b", line, re.IGNORECASE):
        return True

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


def extract_sections(text: str) -> list[tuple[str, str]]:
    """Return (section_title, section_text) pairs."""
    sections: list[tuple[str, str]] = []
    current_title = "General"
    current_lines: list[str] = []

    for raw_line in text.splitlines():
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

    if not sections and text.strip():
        sections.append(("General", text.strip()))

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


def split_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


# ---------------------------------------------------------------------------
# DATABASE SCHEMA VALIDATION
# ---------------------------------------------------------------------------

def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def validate_schema(connection: sqlite3.Connection) -> None:
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

    existing_tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    for table_name, expected_columns in required.items():
        if table_name not in existing_tables:
            raise RuntimeError(
                f"Missing table '{table_name}'. Check the configured database file."
            )

        actual_columns = table_columns(connection, table_name)
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            raise RuntimeError(
                f"Table '{table_name}' is missing columns: {sorted(missing_columns)}"
            )

    print("Database schema validation passed.")


# ---------------------------------------------------------------------------
# DOCUMENT INGESTION
# ---------------------------------------------------------------------------

def ingest_document(
    connection: sqlite3.Connection,
    path: Path,
    domain: str,
    approval_status: str,
) -> int:
    # Domain is intentionally open-ended. Do not use a fixed VALID_DOMAINS set.
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("Document domain must be a non-empty string.")
    domain = domain.strip()

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    file_path = str(path.resolve())
    version = hashlib.sha256(path.read_bytes()).hexdigest()

    existing = connection.execute(
        """
        SELECT document_id, version
        FROM documents
        WHERE file_path = ?
        ORDER BY document_id DESC
        LIMIT 1
        """,
        (file_path,),
    ).fetchone()

    document_id: int
    rebuild_chunks = True

    if existing and existing[1] == version:
        document_id = existing[0]
        total_chunks, missing_titles = connection.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(
                    CASE
                        WHEN section_title IS NULL OR TRIM(section_title) = ''
                        THEN 1 ELSE 0
                    END
                ), 0)
            FROM document_chunks
            WHERE document_id = ?
            """,
            (document_id,),
        ).fetchone()

        if total_chunks > 0 and missing_titles == 0:
            # Refresh metadata even when the file content has not changed.
            # This ensures previously ingested test documents become available
            # to retrieval paths that filter for approved documents.
            connection.execute(
                """
                UPDATE documents
                SET domain = ?, approval_status = ?, ingestion_status = 'completed'
                WHERE document_id = ?
                """,
                (domain, approval_status, document_id),
            )
            print(f"Already ingested; refreshed metadata: {path.name} (document_id={document_id})")
            return document_id

        # Repair chunks only for this document.
        connection.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )
        connection.execute(
            """
            UPDATE documents
            SET domain = ?, approval_status = ?, ingestion_status = 'processing'
            WHERE document_id = ?
            """,
            (domain, approval_status, document_id),
        )
    else:
        # Replace only the prior record for this exact source file.
        if existing:
            old_document_id = existing[0]
            connection.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (old_document_id,),
            )
            connection.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (old_document_id,),
            )

        cursor = connection.execute(
            """
            INSERT INTO documents (
                document_name, domain, version, approval_status,
                file_path, ingestion_status
            )
            VALUES (?, ?, ?, ?, ?, 'processing')
            """,
            (path.name, domain, version, approval_status, file_path),
        )
        document_id = int(cursor.lastrowid)

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
                connection.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_index, section_title,
                        page_number, chunk_text
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        chunk_index,
                        section_title or "General",
                        page_number,
                        chunk,
                    ),
                )
                chunk_index += 1

    connection.execute(
        """
        UPDATE documents
        SET ingestion_status = 'completed'
        WHERE document_id = ?
        """,
        (document_id,),
    )

    print(
        f"Ingested: {path.name} | domain={domain} | "
        f"chunks={chunk_index} | document_id={document_id}"
    )
    return document_id


# ---------------------------------------------------------------------------
# REFERENCE DATA POPULATION
# ---------------------------------------------------------------------------

def populate_reference_data(connection: sqlite3.Connection) -> None:
    """Insert or refresh seeded reference rows as verified test data.

    These records are verified for development/testing so agents can consume
    them during workflow validation. They are not verified company policies.
    No source_document_id is assigned because the values are seeded manually,
    not extracted from a specific source document.
    """
    for name, annual_limit, description in LEAVE_TYPES:
        connection.execute(
            """
            INSERT INTO leave_types (name, annual_limit, description, data_status)
            SELECT ?, ?, ?, 'verified'
            WHERE NOT EXISTS (
                SELECT 1 FROM leave_types WHERE name = ?
            )
            """,
            (name, annual_limit, description, name),
        )
        connection.execute(
            "UPDATE leave_types SET data_status = 'verified' WHERE name = ?",
            (name,),
        )

    for name, description in EXPENSE_CATEGORIES:
        connection.execute(
            """
            INSERT INTO expense_categories (name, description, data_status)
            SELECT ?, ?, 'verified'
            WHERE NOT EXISTS (
                SELECT 1 FROM expense_categories WHERE name = ?
            )
            """,
            (name, description, name),
        )
        connection.execute(
            "UPDATE expense_categories SET data_status = 'verified' WHERE name = ?",
            (name,),
        )

    for role_name, description in ACCESS_ROLES:
        connection.execute(
            """
            INSERT INTO access_roles (role_name, description, data_status)
            SELECT ?, ?, 'verified'
            WHERE NOT EXISTS (
                SELECT 1 FROM access_roles WHERE role_name = ?
            )
            """,
            (role_name, description, role_name),
        )
        connection.execute(
            "UPDATE access_roles SET data_status = 'verified' WHERE role_name = ?",
            (role_name,),
        )

    for domain, rule_name, condition, approver in APPROVAL_RULES:
        connection.execute(
            """
            INSERT INTO approval_rules (
                domain, rule_name, condition_description,
                approver_role, data_status
            )
            SELECT ?, ?, ?, ?, 'verified'
            WHERE NOT EXISTS (
                SELECT 1
                FROM approval_rules
                WHERE domain = ? AND rule_name = ?
            )
            """,
            (domain, rule_name, condition, approver, domain, rule_name),
        )
        connection.execute(
            """
            UPDATE approval_rules
            SET data_status = 'verified'
            WHERE domain = ? AND rule_name = ?
            """,
            (domain, rule_name),
        )

    # Treat every row currently populated in these reference tables as
    # approved development/test data, including pre-existing rows that are
    # not part of the seed lists above. This does not create source links.
    for table_name in (
        "leave_types",
        "expense_categories",
        "access_roles",
        "approval_rules",
    ):
        connection.execute(
            f"UPDATE {table_name} SET data_status = 'verified'"
        )

    print("All populated reference rows marked verified for development/testing.")


# ---------------------------------------------------------------------------
# FTS5 INITIALIZATION
# ---------------------------------------------------------------------------

def initialize_fts(connection: sqlite3.Connection) -> None:
    """Create FTS5 and synchronization triggers, then rebuild the index."""
    connection.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
        USING fts5(
            chunk_text,
            section_title,
            content='document_chunks',
            content_rowid='chunk_id'
        )
        """
    )

    connection.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS document_chunks_ai
        AFTER INSERT ON document_chunks
        BEGIN
            INSERT INTO document_chunks_fts(rowid, chunk_text, section_title)
            VALUES (new.chunk_id, new.chunk_text, new.section_title);
        END;

        CREATE TRIGGER IF NOT EXISTS document_chunks_ad
        AFTER DELETE ON document_chunks
        BEGIN
            INSERT INTO document_chunks_fts(
                document_chunks_fts, rowid, chunk_text, section_title
            )
            VALUES ('delete', old.chunk_id, old.chunk_text, old.section_title);
        END;

        CREATE TRIGGER IF NOT EXISTS document_chunks_au
        AFTER UPDATE ON document_chunks
        BEGIN
            INSERT INTO document_chunks_fts(
                document_chunks_fts, rowid, chunk_text, section_title
            )
            VALUES ('delete', old.chunk_id, old.chunk_text, old.section_title);

            INSERT INTO document_chunks_fts(rowid, chunk_text, section_title)
            VALUES (new.chunk_id, new.chunk_text, new.section_title);
        END;
        """
    )

    connection.execute(
        "INSERT INTO document_chunks_fts(document_chunks_fts) VALUES ('rebuild')"
    )
    print("FTS5 index rebuilt.")


# ---------------------------------------------------------------------------
# INGESTION REPORT
# ---------------------------------------------------------------------------

def print_report(connection: sqlite3.Connection) -> None:
    print("\n========== DOCUMENT COUNTS BY DOMAIN ==========")
    for domain, count in connection.execute(
        """
        SELECT domain, COUNT(*)
        FROM documents
        GROUP BY domain
        ORDER BY domain
        """
    ):
        print(f"{domain}: {count} document(s)")

    print("\n========== CHUNK / SECTION TITLE CHECK ==========")
    for domain, total, missing in connection.execute(
        """
        SELECT
            d.domain,
            COUNT(c.chunk_id),
            COALESCE(SUM(
                CASE
                    WHEN c.section_title IS NULL OR TRIM(c.section_title) = ''
                    THEN 1 ELSE 0
                END
            ), 0)
        FROM documents d
        LEFT JOIN document_chunks c ON c.document_id = d.document_id
        GROUP BY d.domain
        ORDER BY d.domain
        """
    ):
        print(f"{domain}: {total} chunks, {missing} missing section titles")

    print("\n========== REFERENCE TABLE COUNTS ==========")
    for table_name in (
        "leave_types",
        "expense_categories",
        "access_roles",
        "approval_rules",
    ):
        count, verified, linked = connection.execute(
            f"""
            SELECT
                COUNT(*),
                SUM(CASE WHEN data_status = 'verified' THEN 1 ELSE 0 END),
                SUM(CASE WHEN source_document_id IS NOT NULL THEN 1 ELSE 0 END)
            FROM {table_name}
            """
        ).fetchone()
        print(
            f"{table_name}: {count} row(s), "
            f"{verified or 0} verified for testing, "
            f"{linked or 0} linked to source documents"
        )

    print("\n========== DOCUMENT APPROVAL STATUS ==========")
    for status, count in connection.execute(
        "SELECT approval_status, COUNT(*) FROM documents GROUP BY approval_status"
    ):
        print(f"{status}: {count} document(s)")

    print("\n========== SAMPLE CHUNKS ==========")
    rows = connection.execute(
        """
        SELECT
            d.document_name,
            d.domain,
            c.page_number,
            c.section_title,
            SUBSTR(c.chunk_text, 1, 100)
        FROM document_chunks c
        JOIN documents d ON d.document_id = c.document_id
        ORDER BY d.domain, d.document_name, c.chunk_index
        LIMIT 12
        """
    ).fetchall()

    for name, domain, page, title, preview in rows:
        print(
            f"[{domain}] {name} | page={page} | "
            f"section={title} | {preview}"
        )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    create_sample_files()

    # The PDF shown in the sample_documents directory is included.
    # synthetic_company_policy.txt is also included as an example of an
    # additional, non-predefined domain. Its domain label is arbitrary.
    sources: Iterable[tuple[Path, str, str]] = [
        (DOCUMENT_DIR / "HRPolicy 1 2.pdf", "hr", "approved"),
        (DOCUMENT_DIR / "sample_hr_policy.txt", "hr", "approved"),
        (
            DOCUMENT_DIR / "sample_finance_policy.txt",
            "finance",
            "approved",
        ),
        (
            DOCUMENT_DIR / "sample_it_security_policy.txt",
            "it_security",
            "approved",
        ),
        (
            DOCUMENT_DIR / "sample_general_policy.txt",
            "general",
            "approved",
        ),
        (
            DOCUMENT_DIR / "synthetic_company_policy.txt",
            "company_operations",
            "approved",
        ),
    ]

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        validate_schema(connection)

        for path, domain, approval_status in sources:
            if not path.exists():
                # Keep the run useful if an optional/additional source file
                # is absent, but never silently skip the primary HR PDF.
                if path.name == "HRPolicy 1 2.pdf":
                    raise FileNotFoundError(f"Required source PDF not found: {path}")
                print(f"Skipping optional source (not found): {path.name}")
                continue

            ingest_document(connection, path, domain, approval_status)

        populate_reference_data(connection)
        initialize_fts(connection)
        print_report(connection)

    print("\nPopulation and ingestion completed.")


if __name__ == "__main__":
    main()
