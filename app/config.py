"""Configuration for FlowAgent."""
import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    chat_model: str = os.getenv("CHAT_MODEL", "gpt-4o")

    # If DATABASE_URL is set -> persistent Postgres checkpointer (production-style).
    # Otherwise -> in-memory checkpointer so the demo runs with zero infra.
    database_url: str = os.getenv("DATABASE_URL", "")

    # Documents we expect a compliant vendor to provide.
    required_docs: list[str] = os.getenv(
        "REQUIRED_DOCS", "Certificate of Insurance,WSIB Clearance,GST/HST Registration,Signed MSA"
    ).split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()
