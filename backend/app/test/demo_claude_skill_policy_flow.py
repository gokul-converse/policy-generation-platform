"""Live demonstration of the Claude-style skill and policy generation workflow."""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock

from app.agents.policy_generation.policy_generator import StructuredPolicyGenerationOutput
from app.db.session import AsyncSessionLocal
from app.models.policy_api import (
    PolicyGenerationRequest,
    PolicyModificationRequest,
    PolicySectionModel,
)
from app.models.skills import GeneratedSkill, GeneratedSkillSet
from app.services import policy_service, skill_service


async def main():
    print("=" * 80)
    print("STEP 1: USER TYPES '/' IN CHAT (CLAUDE-LIKE AUTOCOMPLETE MENU)")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        commands = await skill_service.get_slash_commands(session)
        for cmd in commands:
            print(f"  {cmd.command:<32} [{cmd.source.upper()}] - {cmd.description[:60]}...")

    print("\n" + "=" * 80)
    print("STEP 2: SKILL GENERATION USING VALIDATED REQUIREMENTS")
    print("=" * 80)

    unique_skill_name = f"annual-leave-rules-{int(time.time()) % 10000}"

    requirements = [
        {
            "requirement_id": "REQ-001",
            "text": "Full-time employees receive 20 days of paid annual leave per year.",
            "numeric_values": ["20 days"],
            "category": "HR",
            "status": "validated",
        },
        {
            "requirement_id": "REQ-002",
            "text": "Leave requests must be submitted at least 5 business days in advance to the reporting manager.",
            "numeric_values": ["5 business days"],
            "category": "HR",
            "status": "validated",
        },
    ]

    # Mock agent for instant deterministic execution
    sample_skill_set = GeneratedSkillSet(
        skills=[
            GeneratedSkill(
                name=unique_skill_name,
                description="Governs annual leave allocation, eligibility, and mandatory advance notice periods.",
                instructions=(
                    f"# Annual Leave Rules\n\n"
                    "## Purpose\n"
                    "Provide clear instructions for calculating and granting annual leave.\n\n"
                    "## Instructions\n"
                    "Grant 20 days of paid annual leave per year. Require 5 business days notice.\n\n"
                    "## Source Requirements\n"
                    "- REQ-001: Full-time employees receive 20 days of paid annual leave per year.\n"
                    "- REQ-002: Leave requests must be submitted at least 5 business days in advance to the reporting manager."
                ),
                requirement_ids=["REQ-001", "REQ-002"],
            )
        ]
    )

    async with AsyncSessionLocal() as session:
        skill_service.generate_skills = AsyncMock(return_value=sample_skill_set)
        saved_skills = await skill_service.generate_and_save_skills(
            session=session,
            validated_requirements=requirements,
            source_requirement_version_id="SNAP-2026-HR-001",
        )

        skill_record = saved_skills[0]
        print(f"Skill Created in DB:")
        print(f"  Skill ID:    {skill_record['skill_id']}")
        print(f"  Name:        {skill_record['name']}")
        print(f"  Description: {skill_record['description']}")
        print(f"  Version:     v{skill_record['version']}")
        print(f"  Status:      {skill_record['status']}")

    print("\n" + "=" * 80)
    print("STEP 3: UPDATED SLASH COMMAND MENU SHOWS NEWLY GENERATED SKILL")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        updated_commands = await skill_service.get_slash_commands(session)
        for cmd in updated_commands:
            print(f"  {cmd.command:<32} [{cmd.source.upper()}] - {cmd.description[:60]}...")

    print("\n" + "=" * 80)
    print("STEP 4: POLICY GENERATION USING /company-policy-generator AND GENERATED SKILL")
    print("=" * 80)

    sample_policy_output = StructuredPolicyGenerationOutput(
        title="Enterprise Annual Leave Policy",
        domain="Human Resources",
        description="Formal corporate guidelines governing employee annual leave entitlements and notice procedures.",
        sections=[
            PolicySectionModel(
                section_id="purpose",
                title="1. Purpose and Scope",
                content="This policy establishes company-wide annual leave entitlements and submission standards for all full-time employees.",
                requirement_ids=["REQ-001"],
            ),
            PolicySectionModel(
                section_id="entitlement",
                title="2. Annual Leave Entitlement",
                content="Full-time employees receive 20 days of paid annual leave per year.",
                requirement_ids=["REQ-001"],
            ),
            PolicySectionModel(
                section_id="notice",
                title="3. Request and Notice Procedures",
                content="Leave requests must be submitted at least 5 business days in advance to the reporting manager.",
                requirement_ids=["REQ-002"],
            ),
        ],
        unresolved_items=[],
    )

    async with AsyncSessionLocal() as session:
        policy_service.generate_policy_from_requirements = AsyncMock(return_value=sample_policy_output)

        policy_req = PolicyGenerationRequest(
            requirements=requirements,  # type: ignore
            skill_command="/company-policy-generator",
            selected_skill_ids=[skill_record["skill_id"]],
            title="Enterprise Annual Leave Policy",
            domain="Human Resources",
            source_requirement_version_id="SNAP-2026-HR-001",
        )

        policy_res = await policy_service.generate_and_save_policy(
            session=session,
            request=policy_req,
        )

        print(f"Policy Created in DB:")
        print(f"  Policy ID:         {policy_res.policy_id}")
        print(f"  Title:             {policy_res.title}")
        print(f"  Description:       {policy_res.description}")
        print(f"  Domain:            {policy_res.domain}")
        print(f"  Version:           v{policy_res.version}")
        print(f"  Validation Status: {policy_res.validation_status.upper()}")
        print(f"  Coverage Score:    {policy_res.validation_report.coverage_score * 100:.1f}%")
        print(f"  Policy Text File:  {policy_res.policy_text_path}")

    print("\n" + "=" * 80)
    print("STEP 5: VERIFY SAVED data/policy.txt ON DISK")
    print("=" * 80)
    policy_txt = Path("data/policy.txt")
    if policy_txt.is_file():
        print(f"File Size: {policy_txt.stat().st_size} bytes")
        print("First 20 lines of data/policy.txt:")
        print("-" * 50)
        lines = policy_txt.read_text(encoding="utf-8").splitlines()[:20]
        for line in lines:
            print(line)
        print("-" * 50)
    else:
        print("ERROR: data/policy.txt was not found!")

    print("\n" + "=" * 80)
    print("STEP 6: POLICY REVISION (CREATES VERSION 2) & APPROVAL")
    print("=" * 80)
    async with AsyncSessionLocal() as session:
        mod_req = PolicyModificationRequest(
            section_id="entitlement",
            instructions="Specify that annual leave is credited per calendar year.",
            updated_content="Full-time employees receive 20 days of paid annual leave per calendar year.",
        )
        v2_res = await policy_service.modify_policy_section(
            session=session,
            policy_id=policy_res.policy_id,
            request=mod_req,
            requirements=requirements,
        )
        print(f"Modified Policy Version: v{v2_res.version} (Status: {v2_res.status})")

        # Approve version 2
        approved_res = await policy_service.approve_policy_version(
            session=session,
            policy_id=policy_res.policy_id,
            version=2,
        )
        print(f"Approved Policy Version: v{approved_res.version} (Status: {approved_res.status})")

        # Verify data/policy.txt updated
        v2_text = policy_txt.read_text(encoding="utf-8")
        print(f"Updated data/policy.txt contains 'calendar year': {'calendar year' in v2_text}")
        print(f"Updated data/policy.txt contains 'Status: APPROVED': {'Status: APPROVED' in v2_text}")

    print("\n" + "=" * 80)
    print("ALL STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
