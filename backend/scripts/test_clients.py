
from app.clients.ollama_client import get_ollama_client
from app.clients.foundry_client import get_foundry_client


def main():
    print("Initializing Ollama client...")
    ollama = get_ollama_client()
    print(f"Ollama client initialized: {type(ollama).__name__}")

    print("\nInitializing Foundry client...")
    foundry = get_foundry_client()
    print(f"Foundry client initialized: {type(foundry).__name__}")


if __name__ == "__main__":
    main()
