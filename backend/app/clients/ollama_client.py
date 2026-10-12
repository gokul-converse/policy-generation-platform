
from functools import lru_cache

from agent_framework.ollama import OllamaChatClient

from app.config.settings import OLLAMA_MODEL


@lru_cache(maxsize=1)                               # Least Recently Used Cache - Python decorator that remembers the result of a function call, so Python can reuse the same object instead of creating it again.
def get_ollama_client() -> OllamaChatClient:
    """Return the shared Ollama chat client."""
    return OllamaChatClient(model=OLLAMA_MODEL)
