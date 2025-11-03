import os
from pydantic_settings import BaseSettings
from typing import ClassVar
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
     # Azure OpenAI credentials
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT_NAME: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"

    # Optional: Add alias for embeddings to avoid breaking imports
    AZURE_EMBEDDING_DEPLOYMENT_NAME: str | None = None

    # # Local configuration
    # # CHROMA_PERSIST_DIR: str = "./chroma_db"
    # CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data/chroma"))
    # os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

     # === Local directories ===
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data/chroma"))

    # === Constants ===
    BASE_DIR: ClassVar[Path] = BASE_DIR

     # OpenAI (fallback)
    OPENAI_API_KEY: str | None = None
    MODEL_NAME: str = "gpt-4o"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Backward compatibility
if not settings.AZURE_EMBEDDING_DEPLOYMENT_NAME and settings.AZURE_OPENAI_DEPLOYMENT_NAME:
    settings.AZURE_EMBEDDING_DEPLOYMENT_NAME = settings.AZURE_OPENAI_DEPLOYMENT_NAME

# Ensure directory exists
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)