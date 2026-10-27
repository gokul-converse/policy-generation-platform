"""End-to-end integration test of the full workflow:
Validated Requirements -> Skill Generation -> Skill Persistence ->
Policy Generation -> Deterministic Validation -> Section Revision -> Approval -> UI Output.
"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.policy_generation.policy_generator import StructuredPolicyGenerationOutput
from app.db.session import Base
from app.models.policy_api import (
    PolicyGenerationRequest,
    PolicyModificationRequest,
    PolicySectionModel,
)
from app.models.skill_api import SkillGenerationRequest
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from app.services import policy_service, skill_service


@pytest.fixture
def mock_skills_and_policy():
    skill_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name="annual-leave-entitlement",
                description="Governs annual leave allocation.",
                instructions=(
                    "# Annual Leave Entitlement\n\n"
                    "## Purpose\n"
                    "Define annual leave rules.\n\n"
                    "## Instructions\n"
                    "Provide 20 days annual leave.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Employees receive 20 days of paid annual leave."
                ),
                requirement_ids=["REQ-001"],
            )
        ]
    )

    policy_output = StructuredPolicyGenerationOutput(
        title="Corporate Leave Policy",
        domain="HR",
        sections=[
            PolicySectionModel(
                section_id="purpose",
                title="Purpose",
                content="This policy establishes guidelines for employee annual leave.",
                requirement_ids=["REQ-001"],
            ),
            PolicySectionModel(
                section_id="entitlement",
                title="Annual Leave Entitlement",
                content="Employees receive 20 days of paid annual leave.",
                requirement_ids=["REQ-001"],
            ),
        ],
        unresolved_items=[],
    )

    return skill_set, policy_output


@pytest.mark.asyncio
async def test_full_end_to_end_workflow(tmp_path, monkeypatch, mock_skills_and_policy):
    mock_skill_set, mock_policy_output = mock_skills_and_policy

    # Isolated test database
    test_db = tmp_path / "test_e2e.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{test_db.as_posix()}")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    # Monkeypatch LLM agents
    mock_gen_skills = AsyncMock(return_value=mock_skill_set)
    monkeypatch.setattr(skill_service, "generate_skills", mock_gen_skills)

    mock_gen_policy = AsyncMock(return_value=mock_policy_output)
    monkeypatch.setattr(policy_service, "generate_policy_from_requirements", mock_gen_policy)

    async with session_factory() as session:
        # Step 1 & 2: Validated Requirements as Source of Truth
        req_inputs = [
            {
                "requirement_id": "REQ-001",
                "text": "Employees receive 20 days of paid annual leave.",
                "numeric_values": ["20 days"],
                "category": "HR",
                "status": "validated",
            }
        ]

        # Step 3: Skill Generation & Persistence
        generated_skills = await skill_service.generate_and_save_skills(
            session=session,
            validated_requirements=req_inputs,
            source_requirement_version_id="SNAP-REQ-001",
        )
        assert len(generated_skills) == 1
        skill_id = generated_skills[0]["skill_id"]
        assert generated_skills[0]["version"] == 1
        assert generated_skills[0]["source_requirement_version_id"] == "SNAP-REQ-001"

        # Step 4: Policy Generation consuming Validated Requirements and Generated Skills
        policy_req = PolicyGenerationRequest(
            requirements=req_inputs,  # type: ignore
            selected_skill_ids=[skill_id],
            title="Corporate Leave Policy",
            domain="HR",
            source_requirement_version_id="SNAP-REQ-001",
        )
        policy_res = await policy_service.generate_and_save_policy(
            session=session,
            request=policy_req,
        )

        assert policy_res.policy_id is not None
        assert policy_res.version == 1
        assert policy_res.status == "draft"
        assert policy_res.validation_status == "pass"
        assert policy_res.validation_report is not None
        assert policy_res.validation_report.coverage_score == 1.0
        assert str(skill_id) in policy_res.applied_skill_ids

        # Step 5 & 6: Policy Review & Modification (Revision creating Version 2)
        mod_req = PolicyModificationRequest(
            section_id="entitlement",
            instructions="Make explicit that entitlement is annual.",
            updated_content="Employees receive 20 days of paid annual leave each working year.",
        )
        v2_policy = await policy_service.modify_policy_section(
            session=session,
            policy_id=policy_res.policy_id,
            request=mod_req,
            requirements=req_inputs,
        )

        assert v2_policy.version == 2
        assert v2_policy.status == "draft"
        assert v2_policy.validation_status == "pass"
        assert "each working year" in v2_policy.sections[1].content

        # Step 7: Approval of Version 2
        approved_policy = await policy_service.approve_policy_version(
            session=session,
            policy_id=policy_res.policy_id,
            version=2,
        )
        assert approved_policy.version == 2
        assert approved_policy.status == "approved"

        # Step 8: Versioned Records & History Retrieval (Structured UI Representation)
        v1_check = await policy_service.get_policy_detail(
            session=session,
            policy_id=policy_res.policy_id,
            version=1,
        )
        assert v1_check is not None
        assert v1_check.version == 1
        assert v1_check.status == "draft"

        v2_check = await policy_service.get_policy_detail(
            session=session,
            policy_id=policy_res.policy_id,
            version=2,
        )
        assert v2_check is not None
        assert v2_check.version == 2
        assert v2_check.status == "approved"
        assert v2_check.validation_report.overall_status == "PASS"

    await test_engine.dispose()
