import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "enterprise_policy.db"


DOMAIN_KEYWORDS = {
    "hr": [
        "leave", "employee", "attendance", "holiday",
        "work from home", "onboarding"
    ],
    "finance": [
        "expense", "reimbursement", "budget",
        "payment", "travel", "invoice"
    ],
    "it_security": [
        "access", "security", "permission", "password",
        "incident", "role", "authentication"
    ],
}

# Only these predefined tables can be queried.
DOMAIN_TABLES = {
    "hr": ["leave_types", "approval_rules"],
    "finance": ["expense_categories", "approval_rules"],
    "it_security": ["access_roles", "approval_rules"],
}

STOPWORDS = {
    "a", "an", "the", "for", "to", "of", "and", "or",
    "our", "company", "create", "make", "generate",
    "prepare", "policy", "please", "with", "in", "on"
}


def identify_domain(description: str) -> str:
    """Identify the likely enterprise domain."""

    text = description.lower()

    scores = {
        domain: sum(
            1 for keyword in keywords
            if keyword in text
        )
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }

    best_domain = max(scores, key=scores.get)

    if scores[best_domain] == 0:
        return "general"

    return best_domain


def extract_keywords(description: str) -> list[str]:
    """Extract simple search terms from the description."""

    words = re.findall(r"[a-zA-Z0-9]+", description.lower())

    return list(dict.fromkeys(
        word for word in words
        if len(word) > 2 and word not in STOPWORDS
    ))


def search_documents(
    conn: sqlite3.Connection,
    keywords: list[str],
    limit: int = 10,
) -> list[dict]:
    """Retrieve matching document chunks using SQLite FTS5."""

    if not keywords:
        return []

    # Quote each token to prevent user text from becoming FTS syntax.
    search_query = " OR ".join(
        '"' + word.replace('"', '""') + '"'
        for word in keywords
    )

    rows = conn.execute(
        """
        SELECT
            d.document_id,
            d.document_name,
            d.domain,
            d.version,
            d.approval_status,
            d.effective_date,
            dc.chunk_id,
            dc.section_title,
            dc.page_number,
            dc.chunk_text
        FROM document_chunks_fts fts
        JOIN document_chunks dc
            ON dc.chunk_id = fts.rowid
        JOIN documents d
            ON d.document_id = dc.document_id
        WHERE document_chunks_fts MATCH ?
        ORDER BY
            CASE WHEN d.approval_status = 'approved'
                 THEN 0 ELSE 1 END,
            d.document_id,
            dc.chunk_index
        LIMIT ?
        """,
        (search_query, limit),
    ).fetchall()

    return [
        {
            "evidence_id": f"ev-doc-{row['chunk_id']}",
            "source_type": "document",
            "source_id": row["document_id"],
            "source_name": row["document_name"],
            "source_version": row["version"],
            "approval_status": row["approval_status"],
            "effective_date": row["effective_date"],
            "location": {
                "chunk_id": row["chunk_id"],
                "section": row["section_title"],
                "page": row["page_number"],
            },
            "content": row["chunk_text"],
        }
        for row in rows
    ]


def search_enterprise_tables(
    conn: sqlite3.Connection,
    domain: str,
) -> list[dict]:
    """Query only predefined tables for the identified domain."""

    table_queries = {
        "leave_types": """
            SELECT leave_type_id, name, annual_limit,
                   carry_forward_allowed, description
            FROM leave_types
        """,
        "expense_categories": """
            SELECT expense_category_id, name, description
            FROM expense_categories
        """,
        "access_roles": """
            SELECT access_role_id, role_name, description,
                   sensitivity_level
            FROM access_roles
        """,
        "approval_rules": """
            SELECT rule_id, domain, rule_name,
                   condition_description, approver_role,
                   is_active, source_document_id
            FROM approval_rules
            WHERE domain = ? AND is_active = 1
        """,
    }

    results = []

    for table in DOMAIN_TABLES.get(domain, []):
        sql = table_queries[table]

        if table == "approval_rules":
            rows = conn.execute(sql, (domain,)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()

        for row in rows:
            record = dict(row)

            results.append({
                "evidence_id": f"ev-db-{table}-{record.get('rule_id', record.get('leave_type_id', record.get('expense_category_id', record.get('access_role_id'))))}",
                "source_type": "sqlite",
                "source_id": table,
                "record_reference": record,
                "approval_status": "unknown",
            })

    return results


def retrieve_evidence(description: str) -> dict:
    """Retrieve relevant enterprise evidence for a policy request."""

    if not description or not description.strip():
        raise ValueError("Policy description cannot be empty.")

    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    domain = identify_domain(description)
    keywords = extract_keywords(description)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        document_evidence = search_documents(conn, keywords)
        database_evidence = search_enterprise_tables(conn, domain)

    return {
        "policy_request": {
            "original_description": description,
            "domain": domain,
        },
        "enterprise_evidence": (
            document_evidence + database_evidence
        ),
        "preliminary_gaps": [],
        "retrieval_metadata": {
            "sources_checked": ["documents", "sqlite"],
            "keywords": keywords,
            "document_evidence_count": len(document_evidence),
            "database_evidence_count": len(database_evidence),
            "retrieval_status": "completed",
        },
    }