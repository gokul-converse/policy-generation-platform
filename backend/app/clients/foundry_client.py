
from functools import lru_cache

from azure.identity.aio import ClientSecretCredential
from agent_framework.foundry import FoundryChatClient

from app.config.settings import (
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
    FOUNDRY_MODEL,
    FOUNDRY_PROJECT_ENDPOINT,
)


@lru_cache(maxsize=1)
def get_foundry_credential() -> ClientSecretCredential:
    """Create the Azure client-secret credential."""
    if not all(
        [
            AZURE_TENANT_ID,
            AZURE_CLIENT_ID,
            AZURE_CLIENT_SECRET,
        ]
    ):
        raise ValueError(
            "Missing Azure tenant, client ID, or client secret."
        )

    return ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )


@lru_cache(maxsize=1)
def get_foundry_client() -> FoundryChatClient:
    """Return the shared Azure AI Foundry chat client."""
    if not FOUNDRY_PROJECT_ENDPOINT or not FOUNDRY_MODEL:
        raise ValueError(
            "FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL must be configured."
        )

    return FoundryChatClient(
        project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
        model=FOUNDRY_MODEL,
        credential=get_foundry_credential(),
    )
