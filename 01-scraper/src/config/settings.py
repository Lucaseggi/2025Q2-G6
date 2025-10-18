import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings


# Nested configuration models for structure
class ServiceConfig(BaseModel):
    """Service configuration"""
    name: str = "enhanced-scraper-ms"
    version: str = "2.0.0"
    port: int = Field(ge=1, le=65535)
    debug: bool = False


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: Optional[str] = None
    region: str = "us-east-1"
    queues: Dict[str, str]


class S3Config(BaseModel):
    """S3 configuration"""
    bucket_name: str
    endpoint: Optional[str] = None
    region: str = "us-east-1"
    access_key_id: str  # Will be set from environment
    secret_access_key: str  # Will be set from environment


class InfolegApiEndpoints(BaseModel):
    """InfoLeg API endpoints"""
    norms_by_year: str
    norm_details: str


class InfolegApiConfig(BaseModel):
    """InfoLeg API configuration"""
    base_url: str
    endpoints: InfolegApiEndpoints
    rate_limit_delay: float = Field(ge=0)
    max_retries: int = Field(ge=0)
    timeout: int = Field(ge=1)
    user_agent: str
    verify_ssl: bool = False

    @field_validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v


class Settings(BaseSettings):
    """Application configuration settings with JSON + env support"""

    # Structured configuration
    service: ServiceConfig
    sqs: SQSConfig
    s3: S3Config
    infoleg_api: InfolegApiConfig

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra fields instead of raising error
    }

    @model_validator(mode='before')
    def load_json_config(cls, values):
        """Load configuration from JSON file and merge with env vars"""
        config_path = Path("config.json")

        if config_path.exists():
            with open(config_path) as f:
                json_config = json.load(f)

            # Merge JSON config with any provided values (env vars take precedence)
            for key, value in json_config.items():
                if key not in values:
                    values[key] = value

        # Add environment variables for nested configs
        if 's3' in values and isinstance(values['s3'], dict):
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            if aws_access_key:
                values['s3']['access_key_id'] = aws_access_key
            if aws_secret_key:
                values['s3']['secret_access_key'] = aws_secret_key

        return values



def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()