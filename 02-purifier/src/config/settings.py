import json
import os
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


class ServiceConfig(BaseModel):
    """Service configuration"""
    name: str = "purifier-ms"
    version: str = "1.0.0"
    port: int = Field(ge=1, le=65535)
    debug: bool = False


class RabbitMQConfig(BaseModel):
    """RabbitMQ configuration"""
    host: str
    port: int = Field(ge=1, le=65535)
    user: str
    vhost: str = "/"
    password: str
    queues: Dict[str, str]


class S3Config(BaseModel):
    """S3 configuration"""
    bucket_name: str
    endpoint: Optional[str] = None
    region: str = "us-east-1"
    access_key_id: str
    secret_access_key: str


class GeminiConfig(BaseModel):
    """Gemini LLM configuration"""
    models: list[str]
    rate_limit: int
    max_input_tokens: int
    max_output_tokens: int
    max_retries: int
    retry_delay: int
    api_keys: list[str] = []


class ProcessingConfig(BaseModel):
    """Processing configuration"""
    batch_size: int
    timeout_seconds: int
    stats_interval_minutes: int


class Settings(BaseSettings):
    """Application configuration settings with JSON + env support"""

    service: ServiceConfig
    rabbitmq: RabbitMQConfig
    s3: S3Config
    gemini: GeminiConfig
    processing: ProcessingConfig

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    @model_validator(mode='before')
    def load_json_config(cls, values):
        """Load configuration from JSON file and merge with env vars"""
        config_path = Path("config.json")

        if config_path.exists():
            with open(config_path) as f:
                json_config = json.load(f)

            for key, value in json_config.items():
                if key not in values:
                    values[key] = value

        # Add environment variables
        if 'rabbitmq' in values and isinstance(values['rabbitmq'], dict):
            rabbitmq_password = os.getenv('RABBITMQ_PASSWORD', 'admin123')
            values['rabbitmq']['password'] = rabbitmq_password

        if 's3' in values and isinstance(values['s3'], dict):
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', 'test')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
            values['s3']['access_key_id'] = aws_access_key
            values['s3']['secret_access_key'] = aws_secret_key

        # Get Gemini API keys from environment
        if 'gemini' in values and isinstance(values['gemini'], dict):
            api_keys = []
            for i in range(1, 6):
                key = os.getenv(f'GEMINI_API_KEY_{i}')
                if key:
                    api_keys.append(key)
            if not api_keys:
                key = os.getenv('GEMINI_API_KEY')
                if key:
                    api_keys.append(key)
            values['gemini']['api_keys'] = api_keys

        return values


def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()
