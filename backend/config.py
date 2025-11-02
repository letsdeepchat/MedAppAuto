"""
Configuration settings for the Medical Appointment Scheduling Agent
"""

import os
from typing import Optional
try:
    from pydantic import BaseSettings, Field
except ImportError:
    # For newer pydantic versions
    from pydantic_settings import BaseSettings
    from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # Vector Database Configuration
    pinecone_api_key: Optional[str] = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(default=None, alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="medical-faq-index", alias="PINECONE_INDEX_NAME")

    # Alternative Vector DB (ChromaDB)
    chroma_db_path: str = Field(default="./data/chroma_db", alias="CHROMA_DB_PATH")

    # Calendly API Configuration
    CALENDLY_API_KEY: Optional[str] = Field(default=None, alias="CALENDLY_API_KEY")
    CALENDLY_BASE_URL: str = Field(default="https://api.calendly.com/v2", alias="CALENDLY_BASE_URL")
    CALENDLY_REFRESH_TOKEN: Optional[str] = Field(default=None, alias="CALENDLY_REFRESH_TOKEN")

    # Clinic Configuration
    clinic_name: str = Field(default="Medical Center", alias="CLINIC_NAME")
    clinic_timezone: str = Field(default="America/New_York", alias="CLINIC_TIMEZONE")

    # Database Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    database_name: str = Field(default="medical_appointments", alias="DATABASE_NAME")

    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Development Settings
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()