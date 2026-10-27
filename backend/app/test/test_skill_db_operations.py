
"""Integration tests for skill database operations."""

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.db.session import Base
from app.models import skill_db  # noqa: F401
from app.models.skill_db import Skill, SkillVersion


@pytest_asyncio.fixture
async def db_session(tmp_path):
    """Create an isolated temporary database for each test."""

    database_path = tmp_path / "test_skills.db"

    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    async with test_session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_create_skill_and_first_version(db_session):
    """Create a skill and persist its first version's metadata."""

    skill = Skill(name="annual-leave-policy")

    skill.versions.append(
        SkillVersion(
            version=1,
            file_path="annual-leave-policy/v1/SKILL.md",
            status="draft",
        )
    )

    db_session.add(skill)
    await db_session.commit()

    result = await db_session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(Skill.name == "annual-leave-policy")
    )

    saved_skill = result.scalar_one()

    assert saved_skill.id is not None
    assert len(saved_skill.versions) == 1

    version = saved_skill.versions[0]

    assert version.id is not None
    assert version.version == 1
    assert version.status == "draft"
    assert version.file_path == "annual-leave-policy/v1/SKILL.md"


@pytest.mark.asyncio
async def test_preserve_previous_skill_version(db_session, tmp_path):
    """Keep approved and draft versions as separate records."""

    skills_root = tmp_path / "generated_skills"

    version_1_path = skills_root / "annual-leave-policy" / "v1" / "SKILL.md"
    version_2_path = skills_root / "annual-leave-policy" / "v2" / "SKILL.md"

    version_1_path.parent.mkdir(parents=True)
    version_2_path.parent.mkdir(parents=True)

    version_1_path.write_text(
        "---\nname: annual-leave-policy\n---\n\n"
        "Employees receive 20 days of annual leave.\n",
        encoding="utf-8",
    )

    version_2_path.write_text(
        "---\nname: annual-leave-policy\n---\n\n"
        "Employees receive 22 days of annual leave.\n",
        encoding="utf-8",
    )

    skill = Skill(name="annual-leave-policy")

    skill.versions.extend(
        [
            SkillVersion(
                version=1,
                file_path=version_1_path.relative_to(skills_root).as_posix(),
                status="approved",
            ),
            SkillVersion(
                version=2,
                file_path=version_2_path.relative_to(skills_root).as_posix(),
                status="draft",
            ),
        ]
    )

    db_session.add(skill)
    await db_session.commit()

    result = await db_session.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill.id)
        .order_by(SkillVersion.version)
    )

    versions = result.scalars().all()

    assert len(versions) == 2

    assert versions[0].version == 1
    assert versions[0].status == "approved"

    original_content = version_1_path.read_text(encoding="utf-8")
    assert "20 days" in original_content

    assert versions[1].version == 2
    assert versions[1].status == "draft"

    updated_content = version_2_path.read_text(encoding="utf-8")
    assert "22 days" in updated_content

    # Updating the draft must not overwrite the approved version.
    assert "20 days" in version_1_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_duplicate_version_number_is_rejected(db_session):
    """Reject duplicate version numbers for the same skill."""

    skill = Skill(name="annual-leave-policy")

    skill.versions.extend(
        [
            SkillVersion(
                version=1,
                file_path="annual-leave-policy/v1/SKILL.md",
                status="approved",
            ),
            SkillVersion(
                version=1,
                file_path="annual-leave-policy/duplicate/SKILL.md",
                status="draft",
            ),
        ]
    )

    db_session.add(skill)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    # The failed transaction should not leave a persisted skill.
    result = await db_session.execute(select(Skill))
    assert result.scalars().all() == []
