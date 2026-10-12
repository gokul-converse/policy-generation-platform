
from typing import Any, Never

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)


class InitialPolicyExecutor(Executor):
    """Simulates the initial policy-generation agent."""

    @handler
    async def process(
        self,
        request: dict[str, Any],
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        print("\n[Executor 1] Generating initial policy...")

        initial_policy = {
            "request_id": request["request_id"],
            "user_input": request["user_input"],
            "initial_policy": {
                "purpose": "Define employee leave rules.",
                "eligibility": "All eligible employees.",
                "leave_entitlement": "Annual leave is provided.",
            },
            "selected_skills": request["selected_skills"],
        }

        print("[Executor 1] Initial policy generated.")

        await ctx.send_message(initial_policy)


class SkillProcessingExecutor(Executor):
    """Simulates loading and applying user-selected skills."""

    @handler
    async def process(
        self,
        data: dict[str, Any],
        ctx: WorkflowContext[dict[str, Any]],
    ) -> None:
        print("\n[Executor 2] Processing selected skills...")

        skills = data["selected_skills"]

        processed_data = {
            **data,
            "skill_instructions": [
                {
                    "skill_id": skill["id"],
                    "instructions": skill["instructions"],
                }
                for skill in skills
            ],
        }

        print(f"[Executor 2] Processed {len(skills)} mock skills.")

        await ctx.send_message(processed_data)


class MasterPolicyExecutor(Executor):
    """Simulates master-policy generation."""

    @handler
    async def process(
        self,
        data: dict[str, Any],
        ctx: WorkflowContext[Never, dict[str, Any]],
    ) -> None:
        print("\n[Executor 3] Generating master policy...")

        skills = data["skill_instructions"]
        initial = data["initial_policy"]

        master_policy = {
            "request_id": data["request_id"],
            "version": 1,
            "status": "awaiting_review",
            "sections": [
                {
                    "id": "purpose",
                    "title": "Purpose",
                    "content": initial["purpose"],
                },
                {
                    "id": "eligibility",
                    "title": "Eligibility",
                    "content": initial["eligibility"],
                },
                {
                    "id": "leave_entitlement",
                    "title": "Leave Entitlement",
                    "content": initial["leave_entitlement"],
                },
            ],
            "applied_skills": [
                skill["skill_id"] for skill in skills
            ],
        }

        print("[Executor 3] Master policy generated.")

        await ctx.yield_output(master_policy)


def build_mock_policy_workflow():
    initial = InitialPolicyExecutor(id="initial_policy")
    skills = SkillProcessingExecutor(id="skill_processing")
    master = MasterPolicyExecutor(id="master_policy")

    workflow = (
        WorkflowBuilder(
            start_executor=initial,
            name="mock-policy-generation",
        )
        .add_chain([initial, skills, master])
        .build()
    )

    return workflow
