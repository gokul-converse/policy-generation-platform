"""Tests for Policy database models and repository operations."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import Base
from app.models.policy_api import PolicySectionModel
from app.models.policy_db import Policy, PolicyVersion
from app.repositories import policy_repository


@pytest_asyncio.fixture
async def db_session(tmp_path):
    test_db = tmp_path / "test_policy_db.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{test_db.as_posix()}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_policy_and_version(db_session):
    sections = [
        PolicySectionModel(
            section_id="sec-1",
            title="Purpose",
            content="To outline company leave policies.",
            requirement_ids=["REQ-001"],
        )
    ]

    policy = await policy_repository.create_policy(
        session=db_session,
        title="Leave Policy",
        domain="HR",
        sections=sections,
        applied_skill_ids=["skill-123"],
        validation_status="pass",
        source_requirement_version_id="SNAP-001",
    )

    assert policy.id is not None
    assert policy.title == "Leave Policy"
    assert len(policy.versions) == 1
    assert policy.versions[0].version == 1
    assert policy.versions[0].status == "draft"
    assert policy.versions[0].source_requirement_version_id == "SNAP-001"


@pytest.mark.asyncio
async def test_create_sequential_versions(db_session):
    sections_v1 = [
        PolicySectionModel(
            section_id="sec-1",
            title="Purpose",
            content="Version 1 content.",
            requirement_ids=["REQ-001"],
        )
    ]
    policy = await policy_repository.create_policy(
        session=db_session,
        title="Travel Policy",
        domain="Finance",
        sections=sections_v1,
    )

    sections_v2 = [
        PolicySectionModel(
            section_id="sec-1",
            title="Purpose",
            content="Version 2 updated content.",
            requirement_ids=["REQ-001"],
        )
    ]
    v2 = await policy_repository.create_policy_version(
        session=db_session,
        policy_id=policy.id,
        sections=sections_v2,
        change_summary="Updated purpose per executive review.",
    )

    assert v2.version == 2
    assert v2.change_summary == "Updated purpose per executive review."

    # Verify both versions exist
    reloaded = await policy_repository.get_policy_by_id(db_session, policy.id)
    assert len(reloaded.versions) == 2
    assert reloaded.versions[0].version == 1
    assert reloaded.versions[1].version == 2


@pytest.mark.asyncio
async def test_update_version_status(db_session):
    sections = [
        PolicySectionModel(
            section_id="sec-1",
            title="Security",
            content="Security guidelines.",
            requirement_ids=["REQ-001"],
        )
    ]
    policy = await policy_repository.create_policy(
        session=db_session,
        title="Security Policy",
        domain="IT",
        sections=sections,
    )

    updated_v = await policy_repository.update_policy_version_status(
        session=db_session,
        policy_id=policy.id,
        version=1,
        new_status="approved",
    )
    assert updated_v.status == "approved"
