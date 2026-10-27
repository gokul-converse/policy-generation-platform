
"""Configure the Microsoft Agent Framework Ollama client."""

from agent_framework.ollama import OllamaChatClient
from app.config.settings import settings


def create_ollama_client() -> OllamaChatClient:
    """Create a client using the application's shared settings."""

    return OllamaChatClient(
        host=settings.ollama_base_url,
        model=settings.ollama_model,
    )
