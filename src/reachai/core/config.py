from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "info"
    DATABASE_URL: str = ""
    LLM_PROVIDER: str = "openai_compatible"
    LLM_MODEL: str = ""
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = ""
    OPENROUTER_BASE_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
