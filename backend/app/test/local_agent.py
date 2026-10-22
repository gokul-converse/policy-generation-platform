"""Test Microsoft Agent Framework with the local Ollama model."""

import asyncio

from agent_framework import Agent
from app.clients.ollama_client import create_ollama_client


async def main() -> None:
    # 1. Create the configured local model client.
    client = create_ollama_client()

    # 2. Create an agent with simple instructions.
    agent = Agent(
        client=client,
        name="LocalModelTestAgent",
        instructions=(
            "You are a concise assistant. "
            "Follow the user's instructions exactly."
        ),
    )

    # 3. Send a test prompt to the model.
    result = await agent.run(
        "Reply with exactly: Local model is working."
    )

    # 4. Display the response.
    print("Agent response:")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
