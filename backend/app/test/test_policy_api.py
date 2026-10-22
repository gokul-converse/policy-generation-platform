"""Integration tests for Policy Generation API endpoints."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.policy_generation.policy_generator import StructuredPolicyGenerationOutput
from app.db.session import Base, get_db
from app.main import app
from app.models.policy_api import PolicySectionModel
from app.services import policy_service


@pytest.fixture
def mock_policy_output():
    return StructuredPolicyGenerationOutput(
        title="Enterprise Annual Leave Policy",
        domain="HR",
        sections=[
            PolicySectionModel(
                section_id="purpose",
                title="Purpose and Scope",
                content="Establishes employee annual leave entitlements and notice guidelines.",
                requirement_ids=["REQ-001"],
            ),
            PolicySectionModel(
                section_id="entitlement",
                title="Leave Entitlement",
                content="Full-time employees receive 20 days of paid annual leave per year.",
                requirement_ids=["REQ-001"],
            ),
        ],
        unresolved_items=[],
    )


@pytest.mark.asyncio
async def test_policy_api_lifecycle(tmp_path, monkeypatch, mock_policy_output):
    """Test full policy API flow: generate -> list -> view -> modify (v2) -> approve."""

    test_db = tmp_path / "test_policy_api.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{test_db.as_posix()}")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Mock policy generation agent
    mock_gen = AsyncMock(return_value=mock_policy_output)
    monkeypatch.setattr(policy_service, "generate_policy_from_requirements", mock_gen)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /policies/generate
        gen_payload = {
            "requirements": [
                {
                    "requirement_id": "REQ-001",
                    "text": "Full-time employees receive 20 days of paid annual leave per year.",
                    "numeric_values": ["20 days"],
                }
            ],
            "title": "Enterprise Annual Leave Policy",
            "domain": "HR",
            "source_requirement_version_id": "SNAP-V1",
        }
        res_gen = await client.post("/policies/generate", json=gen_payload)
        assert res_gen.status_code == 201, res_gen.text
        data = res_gen.json()
        policy_id = data["policy_id"]
        assert data["version"] == 1
        assert data["status"] == "draft"
        assert data["title"] == "Enterprise Annual Leave Policy"
        assert len(data["sections"]) == 2
        assert data["validation_status"] == "pass"

        # 2. GET /policies
        res_list = await client.get("/policies")
        assert res_list.status_code == 200
        policies_list = res_list.json()
        assert len(policies_list) == 1
        assert policies_list[0]["policy_id"] == policy_id

        # 3. GET /policies/{policy_id}
        res_detail = await client.get(f"/policies/{policy_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["policy_id"] == policy_id
        assert detail["version"] == 1

        # 4. POST /policies/{policy_id}/modify (Direct content edit -> version 2)
        mod_payload = {
            "section_id": "entitlement",
            "instructions": "Increase clarity of entitlement statement.",
            "updated_content": "Full-time employees receive 20 days of paid annual leave each calendar year.",
        }
        res_mod = await client.post(f"/policies/{policy_id}/modify", json=mod_payload)
        assert res_mod.status_code == 200, res_mod.text
        mod_data = res_mod.json()
        assert mod_data["version"] == 2
        assert mod_data["status"] == "draft"
        entitlement_sec = next(s for s in mod_data["sections"] if s["section_id"] == "entitlement")
        assert "each calendar year" in entitlement_sec["content"]

        # 5. GET /policies/{policy_id}/versions
        res_vers = await client.get(f"/policies/{policy_id}/versions")
        assert res_vers.status_code == 200
        v_list = res_vers.json()
        assert len(v_list) == 2
        assert [v["version"] for v in v_list] == [1, 2]

        # 6. GET /policies/{policy_id}/versions/1
        res_v1 = await client.get(f"/policies/{policy_id}/versions/1")
        assert res_v1.status_code == 200
        assert res_v1.json()["version"] == 1

        # 7. POST /policies/{policy_id}/versions/2/approve
        res_app = await client.post(f"/policies/{policy_id}/versions/2/approve")
        assert res_app.status_code == 200
        assert res_app.json()["status"] == "approved"
        assert res_app.json()["version"] == 2

        # 8. Check 404 for unknown policy
        fake_id = str(uuid4())
        res_404 = await client.get(f"/policies/{fake_id}")
        assert res_404.status_code == 404

    app.dependency_overrides.clear()
    await test_engine.dispose()
