"""SQLAlchemy models for policy and requirement database tables."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


# 1. Requirement sessions
class RequirementSession(Base):
    __tablename__ = "requirement_sessions"

    session_id = Column(Text, primary_key=True, nullable=False)
    original_description = Column(Text, nullable=False)
    domain = Column(
        Text, nullable=False, server_default=text("'general'")
    )
    status = Column(
        Text, nullable=False, server_default=text("'gathering'")
    )
    created_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        CheckConstraint(
            "domain IN ('hr','finance','it_security','general')"
        ),
        CheckConstraint(
            "status IN ('gathering','awaiting_clarification',"
            "'validating','ready_for_confirmation','confirmed','cancelled')"
        ),
    )

    requirements = relationship(
        "Requirement",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "RequirementVersion",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    validation_runs = relationship(
        "ValidationRun",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    clarification_items = relationship(
        "ClarificationItem",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    messages = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )


# 2. Individual requirements
class Requirement(Base):
    __tablename__ = "requirements"

    requirement_id = Column(Text, primary_key=True, nullable=False)
    session_id = Column(
        Text,
        ForeignKey(
            "requirement_sessions.session_id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    topic = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(
        Text, nullable=False, server_default=text("'extracted'")
    )
    created_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('extracted','needs_clarification',"
            "'validated','confirmed','rejected')"
        ),
    )

    session = relationship("RequirementSession", back_populates="requirements")
    evidence = relationship(
        "RequirementEvidence",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    clarification_items = relationship(
        "ClarificationItem",
        back_populates="requirement",
    )


# 3. Versioned requirement snapshots
class RequirementVersion(Base):
    __tablename__ = "requirement_versions"

    requirement_version_id = Column(Text, primary_key=True, nullable=False)
    session_id = Column(
        Text,
        ForeignKey(
            "requirement_sessions.session_id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    requirements_json = Column(Text, nullable=False)
    validation_status = Column(
        Text, nullable=False, server_default=text("'pending'")
    )
    created_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        UniqueConstraint("session_id", "version_number"),
        CheckConstraint(
            "validation_status IN ('pending','incomplete',"
            "'needs_clarification','valid','confirmed','rejected')"
        ),
    )

    session = relationship("RequirementSession", back_populates="versions")
    validation_runs = relationship(
        "ValidationRun",
        back_populates="requirement_version",
    )


# 4. Validation executions
class ValidationRun(Base):
    __tablename__ = "validation_runs"

    validation_run_id = Column(Text, primary_key=True, nullable=False)
    session_id = Column(
        Text,
        ForeignKey(
            "requirement_sessions.session_id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    requirement_version_id = Column(
        Text,
        ForeignKey(
            "requirement_versions.requirement_version_id",
            ondelete="SET NULL",
        ),
    )
    validation_status = Column(Text, nullable=False)
    findings_json = Column(
        Text, nullable=False, server_default=text("'[]'")
    )
    created_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        CheckConstraint(
            "validation_status IN "
            "('pending','incomplete','needs_clarification','valid','failed')"
        ),
    )

    session = relationship("RequirementSession", back_populates="validation_runs")
    requirement_version = relationship(
        "RequirementVersion",
        back_populates="validation_runs",
    )


# 5. Evidence supporting requirements
class RequirementEvidence(Base):
    __tablename__ = "requirement_evidence"

    evidence_id = Column(Text, primary_key=True, nullable=False)
    requirement_id = Column(
        Text,
        ForeignKey("requirements.requirement_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(Text, nullable=False)
    source_id = Column(Text, nullable=False)
    source_name = Column(Text)
    source_version = Column(Text)
    location = Column(Text)
    evidence_text = Column(Text, nullable=False)
    approval_status = Column(
        Text, nullable=False, server_default=text("'unknown'")
    )

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('document','sqlite','user_input')"
        ),
        CheckConstraint(
            "approval_status IN ('approved','pending_review','rejected',"
            "'sample_not_approved','unknown')"
        ),
    )

    requirement = relationship("Requirement", back_populates="evidence")


# 6. Clarification questions and answers
class ClarificationItem(Base):
    __tablename__ = "clarification_items"

    clarification_id = Column(Text, primary_key=True, nullable=False)
    session_id = Column(
        Text,
        ForeignKey(
            "requirement_sessions.session_id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    requirement_id = Column(
        Text,
        ForeignKey("requirements.requirement_id", ondelete="SET NULL"),
    )
    question = Column(Text, nullable=False)
    answer = Column(Text)
    status = Column(Text, nullable=False, server_default=text("'open'"))
    created_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    answered_at = Column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('open','answered','dismissed')"),
    )

    session = relationship("RequirementSession", back_populates="clarification_items")
    requirement = relationship("Requirement", back_populates="clarification_items")


# 7. Conversation history
class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    message_id = Column(Text, primary_key=True, nullable=False)
    session_id = Column(
        Text,
        ForeignKey(
            "requirement_sessions.session_id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    sender_type = Column(Text, nullable=False)
    agent_name = Column(Text)
    message_type = Column(
        Text, nullable=False, server_default=text("'message'")
    )
    content = Column(Text, nullable=False)
    created_at = Column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        CheckConstraint("sender_type IN ('user','agent','system')"),
        CheckConstraint(
            "message_type IN ('message','clarification_question',"
            "'clarification_answer','status_update','confirmation')"
        ),
    )

    session = relationship("RequirementSession", back_populates="messages")


# 8. Uploaded documents
class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    document_name = Column(Text, nullable=False)
    domain = Column(Text, nullable=False)
    version = Column(Text, nullable=False, server_default=text("'1'"))
    approval_status = Column(
        Text,
        nullable=False,
        server_default=text("'sample_not_approved'"),
    )
    file_path = Column(Text, nullable=False)
    ingestion_status = Column(
        Text, nullable=False, server_default=text("'pending'")
    )

    __table_args__ = (
        UniqueConstraint("file_path", "version"),
        CheckConstraint(
            "domain IN ('hr','finance','it_security','general')"
        ),
        CheckConstraint(
            "approval_status IN ('approved','pending_review','rejected',"
            "'sample_not_approved','unknown')"
        ),
        CheckConstraint(
            "ingestion_status IN ('pending','processing','completed','failed')"
        ),
    )

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


# 9. Extracted document chunks
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    document_id = Column(
        Integer,
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(Text)
    page_number = Column(Integer)
    chunk_text = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
    )

    document = relationship("Document", back_populates="chunks")


# 10. HR leave types
class LeaveType(Base):
    __tablename__ = "leave_types"

    leave_type_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(Text, nullable=False, unique=True)
    annual_limit = Column(Integer)
    description = Column(Text)
    data_status = Column(Text, nullable=False, server_default=text("'sample'"))
    source_document_id = Column(
        Integer,
        ForeignKey("documents.document_id", ondelete="SET NULL"),
    )

    __table_args__ = (
        CheckConstraint("data_status IN ('sample','verified','unknown')"),
    )

    source_document = relationship("Document")


# 11. Finance expense categories
class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    expense_category_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    data_status = Column(Text, nullable=False, server_default=text("'sample'"))
    source_document_id = Column(
        Integer,
        ForeignKey("documents.document_id", ondelete="SET NULL"),
    )

    __table_args__ = (
        CheckConstraint("data_status IN ('sample','verified','unknown')"),
    )

    source_document = relationship("Document")


# 12. IT access roles
class AccessRole(Base):
    __tablename__ = "access_roles"

    access_role_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    role_name = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    data_status = Column(Text, nullable=False, server_default=text("'sample'"))
    source_document_id = Column(
        Integer,
        ForeignKey("documents.document_id", ondelete="SET NULL"),
    )

    __table_args__ = (
        CheckConstraint("data_status IN ('sample','verified','unknown')"),
    )

    source_document = relationship("Document")


# 13. Domain approval rules
class ApprovalRule(Base):
    __tablename__ = "approval_rules"

    rule_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    domain = Column(Text, nullable=False)
    rule_name = Column(Text, nullable=False)
    condition_description = Column(Text, nullable=False)
    approver_role = Column(Text, nullable=False)
    source_document_id = Column(
        Integer,
        ForeignKey("documents.document_id", ondelete="SET NULL"),
    )
    data_status = Column(Text, nullable=False, server_default=text("'sample'"))

    __table_args__ = (
        CheckConstraint(
            "domain IN ('hr','finance','it_security','general')"
        ),
        CheckConstraint("data_status IN ('sample','verified','unknown')"),
    )

    source_document = relationship("Document")
