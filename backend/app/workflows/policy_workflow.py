import json
from typing_extensions import Never
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

from app.agents.requirements_analyzer import analyze_requirements
from app.agents.domain_instruction_generator import generate_domain_instructions
from app.agents.skill_generator import generate_or_reuse_skill
from app.agents.policy_generation.agent import generate_policy


def _decode_state(payload: str) -> dict:
    if isinstance(payload, dict):
        return payload
    return json.loads(payload)


def _encode_state(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False)


class RequirementsAnalyzerExecutor(Executor):
    @handler
    async def process(self, payload: str, ctx: WorkflowContext[str]) -> None:
        state = _decode_state(payload)
        state["requirements"] = await analyze_requirements(
            state["description"], state.get("business_context", "")
        )
        await ctx.send_message(_encode_state(state))


class DomainInstructionExecutor(Executor):
    @handler
    async def process(self, payload: str, ctx: WorkflowContext[str]) -> None:
        state = _decode_state(payload)
        state["domain_instructions"] = await generate_domain_instructions(
            state["requirements"]
        )
        await ctx.send_message(_encode_state(state))


class SkillGeneratorExecutor(Executor):
    @handler
    async def process(self, payload: str, ctx: WorkflowContext[str]) -> None:
        state = _decode_state(payload)
        skill_result = await generate_or_reuse_skill(state["domain_instructions"])
        state["skill_name"] = skill_result["skill_name"]
        state["skill_path"] = skill_result["skill_path"]
        state["skill_reused"] = skill_result["reused"]
        state["skill_text"] = skill_result["skill_text"]
        await ctx.send_message(_encode_state(state))


class PolicyGenerationExecutor(Executor):
    @handler
    async def process(self, payload: str, ctx: WorkflowContext[Never, str]) -> None:
        state = _decode_state(payload)
        policy = await generate_policy(state)
        await ctx.yield_output(policy)


def build_policy_workflow():
    """Build a simple sequential graph: analyzer -> instructions -> skill -> policy."""
    analyzer = RequirementsAnalyzerExecutor(id="requirements_analyzer")
    domain_instructions = DomainInstructionExecutor(id="domain_instruction_generator")
    skill_generator = SkillGeneratorExecutor(id="skill_generator")
    policy_generator = PolicyGenerationExecutor(id="policy_generation")

    return (
        WorkflowBuilder(start_executor=analyzer)
        .add_edge(analyzer, domain_instructions)
        .add_edge(domain_instructions, skill_generator)
        .add_edge(skill_generator, policy_generator)
        .build()
    )


async def run_policy_workflow(description: str, business_context: str = "") -> dict:
    workflow = build_policy_workflow()
    initial_state = {
        "description": description.strip(),
        "business_context": business_context.strip(),
    }
    events = await workflow.run(_encode_state(initial_state))
    outputs = events.get_outputs()
    if not outputs:
        raise RuntimeError("Workflow finished without a policy output.")

    final_state = events.get_final_state()
    return {
        "policy": outputs[-1],
        "final_state": final_state,
    }
