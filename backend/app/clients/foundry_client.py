"""Shared Microsoft Agent Framework Foundry client."""
from agent_framework.foundry import FoundryChatClient
from app.config.settings import settings
from azure.identity import ClientSecretCredential


def get_foundry_credential() -> ClientSecretCredential:
    """Create and cache the Azure client-secret credential."""

    if not all(
        [
            settings.azure_tenant_id,
            settings.azure_client_id,
            settings.azure_client_secret,
        ]
    ):
        raise ValueError(
            "Missing Azure tenant, client ID, or client secret."
        )

    return ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )



def get_foundry_client() -> FoundryChatClient:
    
    if not settings.foundry_project_endpoint or not settings.foundry_model:
        raise ValueError(
            "FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL "
            "must be configured."
        )

    return FoundryChatClient(
        project_endpoint=settings.foundry_project_endpoint,
        model=settings.foundry_model,
        credential=get_foundry_credential(),
    )

