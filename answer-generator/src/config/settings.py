"""Settings and configuration for the answer generator service"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration"""

    # Service settings
    service_name: str = "answer-generator"
    service_port: int = int(os.getenv("SERVICE_PORT", "8042"))
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    debug: bool = os.getenv("DEBUG", "0") == "1"

    # External service URLs
    embedder_api_host: str = os.getenv("EMBEDDER_API_HOST", "http://embedder-api:8001")
    vectorial_api_host: str = os.getenv("VECTORIAL_API_HOST", "http://vectorial-guard:8080")
    relational_api_host: str = os.getenv("RELATIONAL_API_HOST", "http://relational-guard:8090")

    # RAG settings
    default_search_limit: int = int(os.getenv("DEFAULT_SEARCH_LIMIT", "5"))

    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton settings instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
