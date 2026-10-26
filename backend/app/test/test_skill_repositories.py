
"""Tests for the skill repository."""

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config.settings import settings
from app.db.session import Base
from app.models import skill_db  # noqa: F401
from app.models.skill_db import Skill, SkillVersion
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from app.repositories.skill_repository import save_skill_set


@pytest_asyncio.fixture
async def db_session(tmp_path):
    """Create an isolated SQLite database for each test."""

    database_path = tmp_path / "test_skill_repository.db"

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def isolated_skills_directory(tmp_path, monkeypatch):
    """Use a temporary directory for generated Markdown files."""

    skills_directory = tmp_path / "generated_skills"
    skills_directory.mkdir()

    monkeypatch.setattr(
        settings,
        "generated_skills_dir",
        str(skills_directory),
    )

    return skills_directory


def create_sample_skill_set() -> GeneratedSkillSet:
    """Build a representative generated skill set."""

    return GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="annual-leave-policy",
                description="Defines annual leave entitlement.",
                instructions=(
                    "Employees receive 20 days of annual leave."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )


@pytest.mark.asyncio
async def test_create_skill_with_first_version(
    db_session,
    isolated_skills_directory,
):
    """Save a skill and verify its first version's Markdown file."""

    saved = await save_skill_set(
        db_session,
        create_sample_skill_set(),
    )

    assert len(saved) == 1

    skill = saved[0]

    assert skill.id is not None
    assert skill.name == "annual-leave-policy"
    assert len(skill.versions) == 1

    version = skill.versions[0]

    assert version.id is not None
    assert version.version == 1
    assert version.status == "draft"
    assert version.file_path.endswith("/v1/SKILL.md")

    skills_root = isolated_skills_directory.resolve()
    file_path = (skills_root / version.file_path).resolve()

    assert file_path.is_relative_to(skills_root)
    assert file_path.is_file()

    content = file_path.read_text(encoding="utf-8")

    assert "20 days" in content
    assert "annual-leave-policy" in content
    assert "REQ-001" in content


@pytest.mark.asyncio
async def test_duplicate_skill_name_is_rejected(
    db_session,
    isolated_skills_directory,
):
    """Reject duplicate names within a generated set."""

    # GeneratedSkillSet itself now rejects duplicate names at construction
    # time (stronger than the old repository-level check), so save_skill_set
    # is never reached for this case.
    with pytest.raises(ValueError, match="unique"):
        GeneratedSkillSet(
            skills=[
                GeneratedSkill(
                    name="annual-leave-policy",
                    description="First policy.",
                    instructions="First instructions.",
                    requirement_ids=["REQ-001"],
                ),
                GeneratedSkill(
                    name="annual-leave-policy",
                    description="Second policy.",
                    instructions="Second instructions.",
                    requirement_ids=["REQ-002"],
                ),
            ]
        )

    result = await db_session.execute(select(Skill))

    assert result.scalars().all() == []
    assert list(isolated_skills_directory.rglob("SKILL.md")) == []


@pytest.mark.asyncio
async def test_save_skill_set(
    db_session,
    isolated_skills_directory,
):
    """Persist skill metadata and its version metadata."""

    saved = await save_skill_set(
        db_session,
        create_sample_skill_set(),
    )

    assert len(saved) == 1

    result = await db_session.execute(
        select(Skill)
        .options(selectinload(Skill.versions))
        .where(Skill.name == "annual-leave-policy")
    )

    skill = result.scalar_one()

    assert len(skill.versions) == 1
    assert skill.versions[0].version == 1
    assert skill.versions[0].status == "draft"
    assert skill.versions[0].file_path

    assert len(list(isolated_skills_directory.rglob("SKILL.md"))) == 1


@pytest.mark.asyncio
async def test_existing_name_rejects_entire_set(
    db_session,
    isolated_skills_directory,
):
    """Reject a set containing an existing skill name."""

    existing = Skill(name="annual-leave-policy")

    existing.versions.append(
        SkillVersion(
            version=1,
            file_path="existing-skill/v1/SKILL.md",
            status="approved",
        )
    )

    db_session.add(existing)
    await db_session.commit()

    new_skill_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="new-travel-policy",
                description="Travel policy.",
                instructions="Follow travel procedures.",
                requirement_ids=["REQ-002"],
            ),
            GeneratedSkill(
                name="annual-leave-policy",
                description="Conflicting policy.",
                instructions="Conflicting instructions.",
                requirement_ids=["REQ-001"],
            ),
        ]
    )

    with pytest.raises(ValueError, match="already exist"):
        await save_skill_set(db_session, new_skill_set)

    result = await db_session.execute(select(Skill.name))
    names = set(result.scalars().all())

    assert names == {"annual-leave-policy"}

    # No Markdown file should have been written for the rejected set.
    assert list(isolated_skills_directory.rglob("SKILL.md")) == []
