"""Tests for Skill Generation API endpoints."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
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
            "requirements": [
                {
                    "requirement_id": "REQ-001",
                    "text": "Employees receive 20 days vacation per year.",
                }
            ],
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
