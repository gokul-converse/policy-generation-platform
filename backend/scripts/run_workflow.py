import asyncio
from app.workflows.policy_workflow import run_policy_workflow


async def main() -> None:
    print("AI Policy Generation — Graph Workflow")
    print("Enter a policy description. Type 'exit' to quit.\n")

    description = input("Policy description: ").strip()
    if description.lower() in {"exit", "quit"}:
        return

    business_context = input("Business context (optional): ").strip()

    result = await run_policy_workflow(description, business_context)
    print("\n" + "=" * 70)
    print("GENERATED POLICY")
    print("=" * 70)
    print(result["policy"])


if __name__ == "__main__":
    asyncio.run(main())
