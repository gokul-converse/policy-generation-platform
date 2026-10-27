"""Tests for Skill Generation API endpoints."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from app.services import skill_service


@pytest.fixture
def mock_generated_skill_set():
    return GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="vacation-policy",
                description="Manages annual vacation entitlement.",
                instructions=(
                    "# Vacation Policy\n\n"
                    "## Purpose\n"
                    "Manage vacation leave.\n\n"
                    "## Instructions\n"
                    "Provide 20 days vacation per year.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Employees receive 20 days vacation per year."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )


@pytest.mark.asyncio
async def test_skills_api_flow(tmp_path, monkeypatch, mock_generated_skill_set):
    """Test full API lifecycle: generate -> list -> get by ID -> get versions."""

    # Set up isolated in-memory or tmp database
    test_db_path = tmp_path / "test_api.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{test_db_path.as_posix()}")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Seed a confirmed session with one validated requirement so
        # requirement_id="REQ-001" below resolves against something real.
        await conn.execute(text("""
            INSERT INTO requirement_sessions
                (session_id, original_description, domain, status, created_at, updated_at)
            VALUES
                ('SES-001', 'Annual vacation entitlement.', 'hr', 'confirmed', '2026-10-22', '2026-10-22');
        """))
        await conn.execute(text("""
            INSERT INTO requirements
                (requirement_id, session_id, topic, description, status, created_at)
            VALUES
                ('REQ-001', 'SES-001', 'Vacation', 'Employees receive 20 days vacation per year.', 'validated', '2026-10-22');
        """))

    test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Mock LLM generation agent
    mock_gen = AsyncMock(return_value=mock_generated_skill_set)
    monkeypatch.setattr(skill_service, "generate_skills", mock_gen)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /skills/generate
        payload = {
        "requirement_id": "REQ-001",
        "source_requirement_version_id": "SNAP-2026-V1",
        }
        res = await client.post("/skills/generate", json=payload)
        assert res.status_code == 201, res.text
        data = res.json()
        assert "skills" in data
        assert len(data["skills"]) == 1
        skill_id = data["skills"][0]["skill_id"]
        assert data["skills"][0]["name"] == "vacation-policy"
        assert data["skills"][0]["source_requirement_version_id"] == "SNAP-2026-V1"

        # 2. GET /skills
        res_list = await client.get("/skills")
        assert res_list.status_code == 200
        skills_list = res_list.json()
        assert len(skills_list) == 1
        assert skills_list[0]["skill_id"] == skill_id

        # 3. GET /skills/{skill_id}
        res_detail = await client.get(f"/skills/{skill_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["name"] == "vacation-policy"
        assert len(detail["versions"]) == 1
        assert detail["versions"][0]["version"] == 1
        assert detail["versions"][0]["source_requirement_version_id"] == "SNAP-2026-V1"

        # 4. GET /skills/{skill_id}/versions
        res_versions = await client.get(f"/skills/{skill_id}/versions")
        assert res_versions.status_code == 200
        versions = res_versions.json()
        assert len(versions) == 1
        assert versions[0]["version"] == 1

        # 5. GET /skills/{skill_id}/versions/1
        res_v1 = await client.get(f"/skills/{skill_id}/versions/1")
        assert res_v1.status_code == 200
        assert res_v1.json()["version"] == 1
        assert "Vacation Policy" in res_v1.json()["content"]

        # 6. GET 404 for nonexistent skill
        fake_id = str(uuid4())
        res_fake = await client.get(f"/skills/{fake_id}")
        assert res_fake.status_code == 404

        # 7. GET 404 for nonexistent version
        res_fake_v = await client.get(f"/skills/{skill_id}/versions/99")
        assert res_fake_v.status_code == 404

        # 8. POST 422 for invalid request (empty requirements)
        res_bad = await client.post("/skills/generate", json={"requirements": []})
        assert res_bad.status_code == 422

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_skill_list_pagination(tmp_path, monkeypatch):
    """GET /skills respects limit/offset and keeps newest-first order."""

    test_db_path = tmp_path / "test_pagination.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{test_db_path.as_posix()}"
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""
            INSERT INTO requirement_sessions
                (session_id, original_description, domain, status, created_at, updated_at)
            VALUES
                ('SES-PAGE', 'Three unrelated policy topics.', 'hr', 'confirmed', '2026-10-22', '2026-10-22');
        """))
        for i in range(1, 4):
            await conn.execute(
                text("""
                    INSERT INTO requirements
                        (requirement_id, session_id, topic, description, status, created_at)
                    VALUES
                        (:rid, 'SES-PAGE', :topic, :desc, 'validated', '2026-10-22');
                """),
                {
                    "rid": f"REQ-PAGE-{i}",
                    "topic": f"Topic {i}",
                    "desc": f"Requirement number {i}.",
                },
            )

    test_session_factory = async_sessionmaker(
        bind=test_engine, expire_on_commit=False
    )

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async def fake_generate_skills(validated_requirements, client=None, max_retries=3):
        # skill_service passes the adapted list[ValidatedRequirementInput]
        # straight through, not the internal normalized dict shape.
        first_requirement = validated_requirements[0]
        requirement_id = first_requirement.requirement_id
        suffix = requirement_id.rsplit("-", maxsplit=1)[-1]
        return GeneratedSkillSet(
            skills=[
                GeneratedSkill(
                    name=f"skill-{suffix}",
                    description=f"Skill for requirement {requirement_id}.",
                    instructions=(
                        f"# Skill {suffix}\n\n"
                        "## Purpose\nDemo.\n\n"
                        "## Instructions\nDemo.\n\n"
                        "## Source Requirements\n"
                        f"- {requirement_id}: {first_requirement.text}"
                    ),
                    requirement_ids=[requirement_id],
                )
            ]
        )

    monkeypatch.setattr(
        skill_service, "generate_skills", AsyncMock(side_effect=fake_generate_skills)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(1, 4):
            res = await client.post(
                "/skills/generate",
                json={"requirement_id": f"REQ-PAGE-{i}"},
            )
            assert res.status_code == 201, res.text

        # Default: all 3, newest first (highest i last created -> first in list)
        res_all = await client.get("/skills")
        assert res_all.status_code == 200
        all_skills = res_all.json()
        assert len(all_skills) == 3
        assert [s["name"] for s in all_skills] == ["skill-3", "skill-2", "skill-1"]

        # limit=1 -> only the newest
        res_limit = await client.get("/skills", params={"limit": 1})
        assert res_limit.status_code == 200
        limited = res_limit.json()
        assert len(limited) == 1
        assert limited[0]["name"] == "skill-3"

        # limit=1&offset=1 -> the second-newest
        res_offset = await client.get(
            "/skills", params={"limit": 1, "offset": 1}
        )
        assert res_offset.status_code == 200
        offset_result = res_offset.json()
        assert len(offset_result) == 1
        assert offset_result[0]["name"] == "skill-2"

        # offset past the end -> empty, not an error
        res_empty = await client.get("/skills", params={"offset": 10})
        assert res_empty.status_code == 200
        assert res_empty.json() == []

        # limit above the allowed max -> 422
        res_bad_limit = await client.get("/skills", params={"limit": 500})
        assert res_bad_limit.status_code == 422

        # negative offset -> 422
        res_bad_offset = await client.get("/skills", params={"offset": -1})
        assert res_bad_offset.status_code == 422

    app.dependency_overrides.clear()
    await test_engine.dispose()
