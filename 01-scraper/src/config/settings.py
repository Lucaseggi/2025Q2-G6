import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# Import shared secrets manager
sys.path.append('/app/shared')
from secrets_manager import get_secrets_manager


# Nested configuration models for structure
class ServiceConfig(BaseModel):
    """Service configuration (non-sensitive)"""
    name: str = "enhanced-scraper-ms"
    version: str = "2.0.0"
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
    """Application configuration settings with JSON + Secrets Manager support"""

    # Structured configuration
    service: ServiceConfig
    sqs: SQSConfig
    s3: S3Config
    aws: AWSCredentials
    infoleg_api: InfolegApiConfig

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

            # Build SQS config
            if 'sqs' not in values:
                values['sqs'] = {}
            values['sqs']['endpoint'] = aws_config['sqs_endpoint']
            values['sqs']['region'] = aws_config['aws_region']
            if 'queues' not in values['sqs']:
                values['sqs']['queues'] = {}
            # Map logical queue name to actual queue name
            if 'output' in values.get('sqs', {}).get('queues', {}):
                logical_name = values['sqs']['queues']['output']
                values['sqs']['queues']['output'] = queue_names.get(logical_name, logical_name)

            # Build S3 config
            if 's3' not in values:
                values['s3'] = {}
            values['s3']['bucket_name'] = s3_buckets['scraper_bucket']
            values['s3']['endpoint'] = aws_config['s3_endpoint']
            values['s3']['region'] = aws_config['aws_region']

            # Get service port
            values['port'] = service_config['scraper_port']

        except Exception as e:
            # Fallback: SecretsManager will use environment variables
            print(f"Warning: Could not load from Secrets Manager, using env fallback: {e}")

        return values


def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()