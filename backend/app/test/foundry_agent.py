import asyncio

from agent_framework import Agent

from app.clients.foundry_client import (
    get_foundry_client,
    get_foundry_credential,
)


async def main():
    try:
        agent = Agent(
            client=get_foundry_client(),
            name="FoundrySmokeTest",
            instructions="Be concise and follow instructions exactly.",
        )

        result = await agent.run(
            "Reply with exactly: Foundry GPT-5 nano is working."
        )

        print(result.text)

    finally:
        # Close the cached Foundry client if it exposes async cleanup.
        client = get_foundry_client()
        close_client = getattr(client, "aclose", None)

        if close_client is not None:
            await close_client()

        # Close the asynchronous Azure credential.
        credential = get_foundry_credential()
        await credential.close()


if __name__ == "__main__":
    asyncio.run(main())