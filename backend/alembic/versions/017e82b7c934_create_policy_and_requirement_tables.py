"""create policy and requirement tables

Revision ID: 017e82b7c934
Revises: e53b2cb8a85b
Create Date: 2026-10-21 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '017e82b7c934'
down_revision: Union[str, Sequence[str], None] = 'e53b2cb8a85b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema in dependency-safe order.

    Safely reconciles with existing databases: if the tables already exist,
    table creation is skipped to prevent duplicate creation errors or data loss.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. documents table
    if 'documents' not in existing_tables:
        op.create_table(
            'documents',
            sa.Column('document_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('document_name', sa.Text(), nullable=False),
            sa.Column('domain', sa.Text(), nullable=False),
            sa.Column('version', sa.Text(), server_default=sa.text("'1'"), nullable=False),
            sa.Column('approval_status', sa.Text(), server_default=sa.text("'sample_not_approved'"), nullable=False),
            sa.Column('file_path', sa.Text(), nullable=False),
            sa.Column('ingestion_status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
            sa.CheckConstraint("approval_status IN ('approved','pending_review','rejected','sample_not_approved','unknown')"),
            sa.CheckConstraint("domain IN ('hr','finance','it_security','general')"),
            sa.CheckConstraint("ingestion_status IN ('pending','processing','completed','failed')"),
            sa.PrimaryKeyConstraint('document_id'),
            sa.UniqueConstraint('file_path', 'version')
        )

    # 2. document_chunks table
    if 'document_chunks' not in existing_tables:
        op.create_table(
            'document_chunks',
            sa.Column('chunk_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('chunk_index', sa.Integer(), nullable=False),
            sa.Column('section_title', sa.Text(), nullable=True),
            sa.Column('page_number', sa.Integer(), nullable=True),
            sa.Column('chunk_text', sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('chunk_id'),
            sa.UniqueConstraint('document_id', 'chunk_index')
        )

    # 3. document_chunks_fts virtual table and triggers (FTS5 full-text search)
    op.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
        chunk_text,
        section_title,
        content='document_chunks',
        content_rowid='chunk_id'
    );
    """)

    op.execute("""
    CREATE TRIGGER IF NOT EXISTS document_chunks_ai AFTER INSERT ON document_chunks BEGIN
        INSERT INTO document_chunks_fts(rowid, chunk_text, section_title)
        VALUES (new.chunk_id, new.chunk_text, COALESCE(new.section_title, ''));
    END;
    """)

    op.execute("""
    CREATE TRIGGER IF NOT EXISTS document_chunks_ad AFTER DELETE ON document_chunks BEGIN
        INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, section_title)
        VALUES ('delete', old.chunk_id, old.chunk_text, COALESCE(old.section_title, ''));
    END;
    """)

    op.execute("""
    CREATE TRIGGER IF NOT EXISTS document_chunks_au AFTER UPDATE ON document_chunks BEGIN
        INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, section_title)
        VALUES ('delete', old.chunk_id, old.chunk_text, COALESCE(old.section_title, ''));
        INSERT INTO document_chunks_fts(rowid, chunk_text, section_title)
        VALUES (new.chunk_id, new.chunk_text, COALESCE(new.section_title, ''));
    END;
    """)

    # 4. leave_types table
    if 'leave_types' not in existing_tables:
        op.create_table(
            'leave_types',
            sa.Column('leave_type_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('annual_limit', sa.Integer(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('data_status', sa.Text(), server_default=sa.text("'sample'"), nullable=False),
            sa.Column('source_document_id', sa.Integer(), nullable=True),
            sa.CheckConstraint("data_status IN ('sample','verified','unknown')"),
            sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('leave_type_id'),
            sa.UniqueConstraint('name')
        )

    # 5. expense_categories table
    if 'expense_categories' not in existing_tables:
        op.create_table(
            'expense_categories',
            sa.Column('expense_category_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('data_status', sa.Text(), server_default=sa.text("'sample'"), nullable=False),
            sa.Column('source_document_id', sa.Integer(), nullable=True),
            sa.CheckConstraint("data_status IN ('sample','verified','unknown')"),
            sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('expense_category_id'),
            sa.UniqueConstraint('name')
        )

    # 6. access_roles table
    if 'access_roles' not in existing_tables:
        op.create_table(
            'access_roles',
            sa.Column('access_role_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('role_name', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('data_status', sa.Text(), server_default=sa.text("'sample'"), nullable=False),
            sa.Column('source_document_id', sa.Integer(), nullable=True),
            sa.CheckConstraint("data_status IN ('sample','verified','unknown')"),
            sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('access_role_id'),
            sa.UniqueConstraint('role_name')
        )

    # 7. approval_rules table
    if 'approval_rules' not in existing_tables:
        op.create_table(
            'approval_rules',
            sa.Column('rule_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('domain', sa.Text(), nullable=False),
            sa.Column('rule_name', sa.Text(), nullable=False),
            sa.Column('condition_description', sa.Text(), nullable=False),
            sa.Column('approver_role', sa.Text(), nullable=False),
            sa.Column('source_document_id', sa.Integer(), nullable=True),
            sa.Column('data_status', sa.Text(), server_default=sa.text("'sample'"), nullable=False),
            sa.CheckConstraint("data_status IN ('sample','verified','unknown')"),
            sa.CheckConstraint("domain IN ('hr','finance','it_security','general')"),
            sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('rule_id')
        )

    # 8. requirement_sessions table
    if 'requirement_sessions' not in existing_tables:
        op.create_table(
            'requirement_sessions',
            sa.Column('session_id', sa.Text(), nullable=False),
            sa.Column('original_description', sa.Text(), nullable=False),
            sa.Column('domain', sa.Text(), server_default=sa.text("'general'"), nullable=False),
            sa.Column('status', sa.Text(), server_default=sa.text("'gathering'"), nullable=False),
            sa.Column('created_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("domain IN ('hr','finance','it_security','general')"),
            sa.CheckConstraint("status IN ('gathering','awaiting_clarification','validating','ready_for_confirmation','confirmed','cancelled')"),
            sa.PrimaryKeyConstraint('session_id')
        )

    # 9. requirements table
    if 'requirements' not in existing_tables:
        op.create_table(
            'requirements',
            sa.Column('requirement_id', sa.Text(), nullable=False),
            sa.Column('session_id', sa.Text(), nullable=False),
            sa.Column('topic', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('status', sa.Text(), server_default=sa.text("'extracted'"), nullable=False),
            sa.Column('created_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("status IN ('extracted','needs_clarification','validated','confirmed','rejected')"),
            sa.ForeignKeyConstraint(['session_id'], ['requirement_sessions.session_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('requirement_id')
        )

    # 10. requirement_versions table
    if 'requirement_versions' not in existing_tables:
        op.create_table(
            'requirement_versions',
            sa.Column('requirement_version_id', sa.Text(), nullable=False),
            sa.Column('session_id', sa.Text(), nullable=False),
            sa.Column('version_number', sa.Integer(), nullable=False),
            sa.Column('requirements_json', sa.Text(), nullable=False),
            sa.Column('validation_status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
            sa.Column('created_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("validation_status IN ('pending','incomplete','needs_clarification','valid','confirmed','rejected')"),
            sa.ForeignKeyConstraint(['session_id'], ['requirement_sessions.session_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('requirement_version_id'),
            sa.UniqueConstraint('session_id', 'version_number')
        )

    # 11. validation_runs table
    if 'validation_runs' not in existing_tables:
        op.create_table(
            'validation_runs',
            sa.Column('validation_run_id', sa.Text(), nullable=False),
            sa.Column('session_id', sa.Text(), nullable=False),
            sa.Column('requirement_version_id', sa.Text(), nullable=True),
            sa.Column('validation_status', sa.Text(), nullable=False),
            sa.Column('findings_json', sa.Text(), server_default=sa.text("'[]'"), nullable=False),
            sa.Column('created_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("validation_status IN ('pending','incomplete','needs_clarification','valid','failed')"),
            sa.ForeignKeyConstraint(['requirement_version_id'], ['requirement_versions.requirement_version_id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['session_id'], ['requirement_sessions.session_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('validation_run_id')
        )

    # 12. requirement_evidence table
    if 'requirement_evidence' not in existing_tables:
        op.create_table(
            'requirement_evidence',
            sa.Column('evidence_id', sa.Text(), nullable=False),
            sa.Column('requirement_id', sa.Text(), nullable=False),
            sa.Column('source_type', sa.Text(), nullable=False),
            sa.Column('source_id', sa.Text(), nullable=False),
            sa.Column('source_name', sa.Text(), nullable=True),
            sa.Column('source_version', sa.Text(), nullable=True),
            sa.Column('location', sa.Text(), nullable=True),
            sa.Column('evidence_text', sa.Text(), nullable=False),
            sa.Column('approval_status', sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
            sa.CheckConstraint("approval_status IN ('approved','pending_review','rejected','sample_not_approved','unknown')"),
            sa.CheckConstraint("source_type IN ('document','sqlite','user_input')"),
            sa.ForeignKeyConstraint(['requirement_id'], ['requirements.requirement_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('evidence_id')
        )

    # 13. clarification_items table
    if 'clarification_items' not in existing_tables:
        op.create_table(
            'clarification_items',
            sa.Column('clarification_id', sa.Text(), nullable=False),
            sa.Column('session_id', sa.Text(), nullable=False),
            sa.Column('requirement_id', sa.Text(), nullable=True),
            sa.Column('question', sa.Text(), nullable=False),
            sa.Column('answer', sa.Text(), nullable=True),
            sa.Column('status', sa.Text(), server_default=sa.text("'open'"), nullable=False),
            sa.Column('created_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('answered_at', sa.Text(), nullable=True),
            sa.CheckConstraint("status IN ('open','answered','dismissed')"),
            sa.ForeignKeyConstraint(['requirement_id'], ['requirements.requirement_id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['session_id'], ['requirement_sessions.session_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('clarification_id')
        )

    # 14. conversation_messages table
    if 'conversation_messages' not in existing_tables:
        op.create_table(
            'conversation_messages',
            sa.Column('message_id', sa.Text(), nullable=False),
            sa.Column('session_id', sa.Text(), nullable=False),
            sa.Column('sender_type', sa.Text(), nullable=False),
            sa.Column('agent_name', sa.Text(), nullable=True),
            sa.Column('message_type', sa.Text(), server_default=sa.text("'message'"), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.Text(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.CheckConstraint("message_type IN ('message','clarification_question','clarification_answer','status_update','confirmation')"),
            sa.CheckConstraint("sender_type IN ('user','agent','system')"),
            sa.ForeignKeyConstraint(['session_id'], ['requirement_sessions.session_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('message_id')
        )


def downgrade() -> None:
    """Downgrade schema in reverse dependency order.

    Removes only the objects introduced by this migration without dropping the skill tables.
    """
    # 1. Drop FTS triggers and virtual table
    op.execute("DROP TRIGGER IF EXISTS document_chunks_au")
    op.execute("DROP TRIGGER IF EXISTS document_chunks_ad")
    op.execute("DROP TRIGGER IF EXISTS document_chunks_ai")
    op.execute("DROP TABLE IF EXISTS document_chunks_fts")

    # 2. Drop application tables in reverse dependency order
    op.drop_table('conversation_messages')
    op.drop_table('clarification_items')
    op.drop_table('requirement_evidence')
    op.drop_table('validation_runs')
    op.drop_table('requirement_versions')
    op.drop_table('requirements')
    op.drop_table('requirement_sessions')
    op.drop_table('approval_rules')
    op.drop_table('access_roles')
    op.drop_table('expense_categories')
    op.drop_table('leave_types')
    op.drop_table('document_chunks')
    op.drop_table('documents')
