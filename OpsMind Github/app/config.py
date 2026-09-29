"""Application configuration and environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if it exists
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    """Central configuration for OpsMind."""

    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "127.0.0.1")
    OPSMIND_ENV: str = os.getenv("OPSMIND_ENV", "development")

    # Hindsight Persistent Memory
    HINDSIGHT_API_KEY: str | None = os.getenv("HINDSIGHT_API_KEY") or None
    HINDSIGHT_API_URL: str = os.getenv(
        "HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io"
    ).rstrip("/")
    HINDSIGHT_BANK_ID: str = os.getenv("HINDSIGHT_BANK_ID", "opsmind-incidents")

    # LLM Provider
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY") or None
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    @property
    def has_hindsight_credentials(self) -> bool:
        """Returns True if Hindsight credentials are configured."""
        return bool(self.HINDSIGHT_API_KEY and self.HINDSIGHT_API_KEY.strip())

    @property
    def has_llm_credentials(self) -> bool:
        """Returns True if Groq/LLM credentials are configured."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())


settings = Settings()
