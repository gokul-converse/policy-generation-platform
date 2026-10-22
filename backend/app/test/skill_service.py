
"""Tests for the skill application service."""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from app.db.session import Base
from app.models import skill_db  # noqa: F401
from app.models.skill_db import Skill, SkillVersion
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from app.services import skill_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'service_test.db').as_posix()}"
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_and_save_skills(db_session, monkeypatch):
    generated_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="annual-leave-policy",
                description="Defines annual leave entitlement.",
                instructions="Employees receive 20 days of annual leave.",
                requirement_ids=["REQ-001"],
            )
        ]
    )

    mock_generate = AsyncMock(return_value=generated_set)
    monkeypatch.setattr(
        skill_service,
        "generate_skills",
        mock_generate,
    )

    requirements = {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "text": "Employees receive 20 days of annual leave.",
            }
        ]
    }

    result = await skill_service.generate_and_save_skills(
        db_session,
        requirements,
    )

    assert len(result) == 1
    assert result[0]["skill_id"] is not None
    assert result[0]["version_id"] is not None
    assert result[0]["version"] == 1
    assert result[0]["status"] == "draft"

    mock_generate.assert_awaited_once_with(requirements)

    saved = await db_session.execute(select(Skill))
    assert len(saved.scalars().all()) == 1

    versions = await db_session.execute(select(SkillVersion))
    assert len(versions.scalars().all()) == 1


@pytest.mark.asyncio
async def test_generation_failure_does_not_save_skills(
    db_session,
    monkeypatch,
):
    mock_generate = AsyncMock(
        side_effect=RuntimeError("Agent generation failed")
    )
    monkeypatch.setattr(
        skill_service,
        "generate_skills",
        mock_generate,
    )

    with pytest.raises(RuntimeError, match="Agent generation failed"):
        await skill_service.generate_and_save_skills(
            db_session,
            {
                "requirements": [
                    {
                        "requirement_id": "REQ-001",
                        "text": "Employees receive 20 days of annual leave.",
                    }
                ]
            },
        )

    saved = await db_session.execute(select(Skill))
    assert len(saved.scalars().all()) == 0

    versions = await db_session.execute(select(SkillVersion))
    assert len(versions.scalars().all()) == 0
