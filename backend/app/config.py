from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    LLM_PROVIDER: Literal["grok", "claude"] = "grok"
    XAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./data/yt_summarizer.db"
    PDF_DIR: str = "./data/pdfs"
    ENCRYPTION_KEY: str = ""
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
