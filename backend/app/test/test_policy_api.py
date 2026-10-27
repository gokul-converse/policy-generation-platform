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
            "session_id": "SES-DEMO-001",
            "requirement_id": "REQ-DEMO-001",
            "title": "Enterprise Annual Leave Policy",
            "domain": "HR",
            "source_requirement_version_id": "REQ-DEMO-001",
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


@pytest.mark.asyncio
async def test_policy_list_filters_and_pagination(tmp_path, monkeypatch):
    """GET /policies respects domain, status, limit, and offset."""

    test_db = tmp_path / "test_policy_pagination.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{test_db.as_posix()}")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    def make_output(title: str, domain: str) -> StructuredPolicyGenerationOutput:
        return StructuredPolicyGenerationOutput(
            title=title,
            domain=domain,
            sections=[
                PolicySectionModel(
                    section_id="purpose",
                    title="Purpose",
                    content=f"Purpose of {title}.",
                    requirement_ids=["REQ-001"],
                ),
            ],
            unresolved_items=[],
        )

    outputs = [
        make_output("HR Leave Policy", "hr"),
        make_output("Finance Expense Policy", "finance"),
        make_output("HR Onboarding Policy", "hr"),
    ]
    mock_gen = AsyncMock(side_effect=outputs)
    monkeypatch.setattr(
        policy_service, "generate_policy_from_requirements", mock_gen
    )

    def gen_payload(title: str) -> dict:
        return {
            "session_id": "SES-DEMO-001",
            "requirement_id": "REQ-DEMO-001",
            "title": title,
            "domain": "HR",
            "source_requirement_version_id": "REQ-DEMO-001",
        }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created_ids = []
        for title in (
            "HR Leave Policy",
            "Finance Expense Policy",
            "HR Onboarding Policy",
        ):
            res = await client.post("/policies/generate", json=gen_payload(title))
            assert res.status_code == 201, res.text
            created_ids.append(res.json()["policy_id"])

        # No filters -> all 3, newest first
        res_all = await client.get("/policies")
        assert res_all.status_code == 200
        all_policies = res_all.json()
        assert len(all_policies) == 3
        assert [p["title"] for p in all_policies] == [
            "HR Onboarding Policy",
            "Finance Expense Policy",
            "HR Leave Policy",
        ]

        # domain filter -> only the 2 HR policies
        res_hr = await client.get("/policies", params={"domain": "hr"})
        assert res_hr.status_code == 200
        hr_policies = res_hr.json()
        assert len(hr_policies) == 2
        assert all(p["title"].startswith("HR") for p in hr_policies)

        # status filter -> approve one, then only it should show status=approved
        approve_id = created_ids[0]  # "HR Leave Policy"
        res_approve = await client.post(
            f"/policies/{approve_id}/versions/1/approve"
        )
        assert res_approve.status_code == 200

        res_approved = await client.get("/policies", params={"status": "approved"})
        assert res_approved.status_code == 200
        approved_policies = res_approved.json()
        assert len(approved_policies) == 1
        assert approved_policies[0]["policy_id"] == approve_id

        res_draft = await client.get("/policies", params={"status": "draft"})
        assert res_draft.status_code == 200
        assert len(res_draft.json()) == 2

        # combined domain + status
        res_combo = await client.get(
            "/policies", params={"domain": "hr", "status": "draft"}
        )
        assert res_combo.status_code == 200
        combo = res_combo.json()
        assert len(combo) == 1
        assert combo[0]["title"] == "HR Onboarding Policy"

        # invalid status value -> 422, not silently ignored
        res_bad_status = await client.get(
            "/policies", params={"status": "not-a-real-status"}
        )
        assert res_bad_status.status_code == 422

        # pagination
        res_page = await client.get("/policies", params={"limit": 1, "offset": 1})
        assert res_page.status_code == 200
        page = res_page.json()
        assert len(page) == 1
        assert page[0]["title"] == "Finance Expense Policy"

    app.dependency_overrides.clear()
    await test_engine.dispose()
