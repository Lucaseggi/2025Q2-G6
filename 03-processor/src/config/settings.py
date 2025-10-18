"""Configuration management for processor service using Pydantic"""

import json
import os
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


class ServiceConfig(BaseModel):
    """Service configuration"""
    name: str = "processor-ms"
    version: str = "1.0.0"
    port: int = Field(ge=1, le=65535, default=8005)
    debug: bool = False


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: Optional[str] = None
    region: str = "us-east-1"
    queues: Dict[str, str]

    @model_validator(mode='before')
    def override_from_env(cls, values):
        """Override with environment variables (for Lambda)"""
        if os.getenv('SQS_ENDPOINT'):
            values['endpoint'] = os.getenv('SQS_ENDPOINT')
        if os.getenv('AWS_DEFAULT_REGION'):
            values['region'] = os.getenv('AWS_DEFAULT_REGION')
        if os.getenv('PROCESSING_QUEUE_NAME') and 'queues' in values:
            values['queues']['input'] = os.getenv('PROCESSING_QUEUE_NAME')
        if os.getenv('EMBEDDING_QUEUE_NAME') and 'queues' in values:
            values['queues']['output'] = os.getenv('EMBEDDING_QUEUE_NAME')
        return values


class S3Config(BaseModel):
    """S3 configuration"""
    bucket_name: str
    endpoint: Optional[str] = None
    region: str = "us-east-1"
    access_key_id: str = ""
    secret_access_key: str = ""

    @model_validator(mode='before')
    def override_from_env(cls, values):
        """Override with environment variables (for Lambda)"""
        if os.getenv('S3_BUCKET_NAME'):
            values['bucket_name'] = os.getenv('S3_BUCKET_NAME')
        if os.getenv('S3_ENDPOINT'):
            values['endpoint'] = os.getenv('S3_ENDPOINT')
        if os.getenv('AWS_DEFAULT_REGION'):
            values['region'] = os.getenv('AWS_DEFAULT_REGION')
        return values


class GeminiConfig(BaseModel):
    """Gemini LLM configuration"""
    models: list[str]
    rate_limit: int
    max_input_tokens: int
    max_output_tokens: int
    max_retries: int
    retry_delay: int
    diff_threshold: float
    api_keys: list[str] = []


class ProcessingConfig(BaseModel):
    """Processing configuration"""
    batch_size: int
    timeout_seconds: int
    stats_interval_minutes: int


class Settings(BaseSettings):
    """Application configuration settings with JSON + env support"""

    service: ServiceConfig
    sqs: SQSConfig
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

        # Add environment variables for S3
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


# Backwards compatibility alias
ProcessorSettings = Settings
