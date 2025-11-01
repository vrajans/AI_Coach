import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
     # Azure OpenAI credentials
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT_NAME: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"

    # Optional: Add alias for embeddings to avoid breaking imports
    AZURE_EMBEDDING_DEPLOYMENT_NAME: str | None = None

    # Local configuration
    CHROMA_PERSIST_DIR: str = "./chroma_db"

     # OpenAI (fallback)
    OPENAI_API_KEY: str | None = None
    MODEL_NAME: str = "gpt-4o"

    class Config:
        env_file = ".env"

settings = Settings()

# Backward compatibility
if not settings.AZURE_EMBEDDING_DEPLOYMENT_NAME and settings.AZURE_OPENAI_DEPLOYMENT_NAME:
    settings.AZURE_EMBEDDING_DEPLOYMENT_NAME = settings.AZURE_OPENAI_DEPLOYMENT_NAME