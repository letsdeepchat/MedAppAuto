"""
Configuration settings for the Medical Appointment Scheduling Agent
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LLM Configuration
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # Vector Database Configuration
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("medical-faq-index", env="PINECONE_INDEX_NAME")

    # Alternative Vector DB (ChromaDB)
    chroma_db_path: str = Field("./data/chroma_db", env="CHROMA_DB_PATH")

    # Calendly API Configuration
    calendly_api_key: Optional[str] = Field(None, env="CALENDLY_API_KEY")
    calendly_base_url: str = Field("https://api.calendly.com/v2", env="CALENDLY_BASE_URL")

    # Clinic Configuration
    clinic_name: str = Field("Medical Center", env="CLINIC_NAME")
    clinic_timezone: str = Field("America/New_York", env="CLINIC_TIMEZONE")

    # Database Configuration
    mongodb_url: str = Field("mongodb://localhost:27017", env="MONGODB_URL")
    database_name: str = Field("medical_appointments", env="DATABASE_NAME")

    # Server Configuration
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")

    # Development Settings
    debug: bool = Field(True, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()