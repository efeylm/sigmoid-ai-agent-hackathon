# Configuration Settings
# Environment variables and application configuration
# Loads settings from .env file
# Contains API keys, database URLs, and other config values

from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = "Sigmoid AI Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database - Must be set in .env file
    DATABASE_URL: str
    DB_ECHO: bool = False
    IMAGE_STORAGE_BASE_PATH: str = "/app"  # Docker içindeki base path
    # AI & Services
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-6-luna"
    # gpt-6-luna is a reasoning model; Chat Completions tool calling requires "none".
    # Leave empty for models that do not support reasoning_effort.
    OPENAI_REASONING_EFFORT: Optional[str] = "none"
    OPENAI_TEMPERATURE: Optional[float] = None
    # Set to true only for models that accept a custom temperature.
    OPENAI_SEND_TEMPERATURE: bool = False
    TAVILY_API_KEY: str

    @field_validator("OPENAI_REASONING_EFFORT", "OPENAI_TEMPERATURE", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        return None if v == "" else v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()

