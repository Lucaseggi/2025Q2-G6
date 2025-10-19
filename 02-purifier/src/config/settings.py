import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings

# Import shared secrets manager
sys.path.append('/app/shared')
from secrets_manager import get_secrets_manager


class ServiceConfig(BaseModel):
    """Service configuration (non-sensitive)"""
    name: str = "purifier-ms"
    version: str = "1.0.0"
    debug: bool = False


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: str  # From secrets
    region: str  # From secrets
    queues: Dict[str, str]  # Logical queue names


class S3Config(BaseModel):
    """S3 configuration"""
    bucket_name: str  # From secrets
    endpoint: str  # From secrets
    region: str  # From secrets


class AWSCredentials(BaseModel):
    """AWS credentials (from secrets)"""
    access_key_id: str
    secret_access_key: str
    region: str


class GeminiConfig(BaseModel):
    """Gemini LLM configuration (algorithm parameters from config.json)"""
    models: list[str]
    rate_limit: int
    max_input_tokens: int
    max_output_tokens: int
    max_retries: int
    retry_delay: int
    api_key: str  # From secrets


class ProcessingConfig(BaseModel):
    """Processing configuration (algorithm parameters from config.json)"""
    batch_size: int
    timeout_seconds: int
    stats_interval_minutes: int


class Settings(BaseSettings):
    """Application configuration settings with JSON + Secrets Manager support"""

    service: ServiceConfig
    sqs: SQSConfig
    s3: S3Config
    aws: AWSCredentials
    gemini: GeminiConfig
    processing: ProcessingConfig

    # Service-specific runtime config
    port: int = Field(ge=1, le=65535)

    model_config = {
        "case_sensitive": False,
        "extra": "ignore"
    }

    @model_validator(mode='before')
    def load_config(cls, values):
        """Load configuration from config.json + AWS Secrets Manager"""
        # 1. Load algorithm parameters from config.json
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path) as f:
                json_config = json.load(f)

            # Merge JSON config (non-sensitive params)
            for key, value in json_config.items():
                if key not in values:
                    values[key] = value

        # 2. Load sensitive data from AWS Secrets Manager
        try:
            secrets = get_secrets_manager()

            # Get AWS config
            aws_config = secrets.get_secret('simpla/shared/aws-config')
            values['aws'] = {
                'access_key_id': aws_config['aws_access_key_id'],
                'secret_access_key': aws_config['aws_secret_access_key'],
                'region': aws_config['aws_region']
            }

            # Get queue names
            queue_names = secrets.get_secret('simpla/shared/queue-names')

            # Get S3 buckets
            s3_buckets = secrets.get_secret('simpla/shared/s3-buckets')

            # Get service config
            service_config = secrets.get_secret('simpla/services/config')

            # Get API keys
            gemini_keys = secrets.get_secret('simpla/api-keys/gemini')

            # Build SQS config
            if 'sqs' not in values:
                values['sqs'] = {}
            values['sqs']['endpoint'] = aws_config['sqs_endpoint']
            values['sqs']['region'] = aws_config['aws_region']
            if 'queues' not in values['sqs']:
                values['sqs']['queues'] = {}
            # Map logical queue names to actual queue names
            for queue_type in ['input', 'output']:
                if queue_type in values.get('sqs', {}).get('queues', {}):
                    logical_name = values['sqs']['queues'][queue_type]
                    values['sqs']['queues'][queue_type] = queue_names.get(logical_name, logical_name)

            # Build S3 config
            if 's3' not in values:
                values['s3'] = {}
            values['s3']['bucket_name'] = s3_buckets['purifier_bucket']
            values['s3']['endpoint'] = aws_config['s3_endpoint']
            values['s3']['region'] = aws_config['aws_region']

            # Add Gemini API key to gemini config
            if 'gemini' not in values:
                values['gemini'] = {}
            values['gemini']['api_key'] = gemini_keys['api_key']

            # Get service port
            values['port'] = service_config['purifier_port']

        except Exception as e:
            # Fallback: SecretsManager will use environment variables
            print(f"Warning: Could not load from Secrets Manager, using env fallback: {e}")

        return values


def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()
