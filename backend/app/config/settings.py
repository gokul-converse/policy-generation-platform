"""Central configuration for the policy-generation backend."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # ---------------------------------------------------------
    # LLM configuration
    # ---------------------------------------------------------

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # ---------------------------------------------------------
    # Database configuration
    # ---------------------------------------------------------

    database_url: str = Field(
        default="sqlite+aiosqlite:///./policy_generation.db",
        description="SQLAlchemy asynchronous database URL.",
    )

    # ---------------------------------------------------------
    # Built-in skills configuration
    # Built-in skills are used ONLY by Skill Generation Agent.
    # Generated skills are maintained in the database.
    # ---------------------------------------------------------

    builtin_skills_dir: str = "skills"

    skill_generation_builtin_skill_name: str = "company-policy-generator"

    # ---------------------------------------------------------
    # Azure identity configuration
    # ---------------------------------------------------------

    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # ---------------------------------------------------------
    # Azure AI Foundry configuration
    # ---------------------------------------------------------

    foundry_project_endpoint: str = ""
    foundry_model: str = "gpt-5-nano"

    # ---------------------------------------------------------
    # Logging configuration
    # ---------------------------------------------------------

    log_dir: str = "logs"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------------------------------------------------
    # Application paths
    # ---------------------------------------------------------

    @property
    def BACKEND_ROOT(self) -> Path:
        """Return the absolute backend root directory."""
        return BACKEND_ROOT

    @property
    def backend_root(self) -> Path:
        """Return the absolute backend root directory."""
        return BACKEND_ROOT

    @property
    def builtin_skills_path(self) -> Path:
        """Return the configured built-in skills directory."""

        path = Path(self.builtin_skills_dir)

        if not path.is_absolute():
            path = BACKEND_ROOT / path

        return path.resolve()

    @property
    def skill_generation_builtin_skill_path(self) -> Path:
        """Return the configured Skill Generation built-in skill path."""

        return (
            self.builtin_skills_path
            / self.skill_generation_builtin_skill_name
        ).resolve()

    @property
    def log_path(self) -> Path:
        """Return the absolute application log directory."""

        path = Path(self.log_dir)

        if not path.is_absolute():
            path = BACKEND_ROOT / path

        return path.resolve()


settings = Settings()
