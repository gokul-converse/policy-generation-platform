import os

from dotenv import load_dotenv

load_dotenv()

# Ollama
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "Llama3.2:3b")

# Azure AI Foundry
FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
FOUNDRY_MODEL = os.getenv(
    "FOUNDRY_MODEL",
    os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
