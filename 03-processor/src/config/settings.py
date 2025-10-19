"""Configuration management for processor service using Pydantic with Secrets Manager"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings

# Import shared secrets manager
sys.path.append('/app/shared')
from secrets_manager import SecretsManager


class ServiceConfig(BaseModel):
    """Service configuration (non-sensitive)"""
    name: str = "processor-ms"
    version: str = "2.0"
    debug: bool = False


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: Optional[str] = None  # None for AWS Lambda
    region: str
    queues: Dict[str, str]  # Actual queue names


class S3Config(BaseModel):
    """S3 configuration"""
    bucket_name: str
    endpoint: Optional[str] = None  # None for AWS Lambda
    region: str


class AWSCredentials(BaseModel):
    """AWS credentials (empty for Lambda, populated for LocalStack)"""
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: str


class GeminiConfig(BaseModel):
    """Gemini LLM configuration (algorithm parameters from config.json)"""
    models: list[str]
    rate_limit: int
    max_input_tokens: int
    max_output_tokens: int
    max_retries: int
    retry_delay: int
    diff_threshold: float
    api_key: str  # From secrets


class ProcessingConfig(BaseModel):
    """Processing configuration"""
    batch_size: int
    timeout_seconds: int
    stats_interval_minutes: int


class EnvironmentConfig(BaseModel):
    """Environment detection and configuration"""
    is_localstack: bool
    is_lambda: bool
    secrets_manager_endpoint: Optional[str] = None
    aws_region: str
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None


class Settings(BaseSettings):
    """
    Application configuration with centralized environment detection.

    Settings is the injected dependency that services receive.
    Services never access os.getenv() - everything comes from Settings.
    """

    # Environment detection
    environment: EnvironmentConfig

    # Configuration
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

    @staticmethod
    def _detect_environment() -> EnvironmentConfig:
        """Detect environment (LocalStack vs Lambda). ONLY place with env detection."""
        localstack_indicators = [
            'localstack' in os.getenv('SQS_ENDPOINT', '').lower(),
            'localstack' in os.getenv('S3_ENDPOINT', '').lower(),
            'localstack' in os.getenv('SECRETS_MANAGER_ENDPOINT', '').lower(),
            os.getenv('USE_LOCALSTACK', '').lower() == 'true',
            os.getenv('AWS_ACCESS_KEY_ID') == 'test'
        ]
        is_localstack = any(localstack_indicators)
        is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ and not is_localstack

        env_config = {
            'is_localstack': is_localstack,
            'is_lambda': is_lambda,
            'aws_region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }

        if is_localstack:
            env_config['secrets_manager_endpoint'] = os.getenv('SECRETS_MANAGER_ENDPOINT', 'http://localstack:4566')
            env_config['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID', 'test')
            env_config['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        else:
            env_config['secrets_manager_endpoint'] = None
            env_config['aws_access_key_id'] = None
            env_config['aws_secret_access_key'] = None

        return EnvironmentConfig(**env_config)

    @model_validator(mode='before')
    def load_config(cls, values):
        """Load configuration from environment + config.json + Secrets Manager"""

        # STEP 1: Detect environment
        env_config = cls._detect_environment()
        values['environment'] = env_config.model_dump()

        # STEP 2: Load algorithm parameters from config.json
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path) as f:
                json_config = json.load(f)
            for key, value in json_config.items():
                if key not in values:
                    values[key] = value

        # STEP 3: Configure SecretsManager explicitly (no auto-detection)
        secrets = SecretsManager(
            endpoint_url=env_config.secrets_manager_endpoint,
            region_name=env_config.aws_region,
            aws_access_key_id=env_config.aws_access_key_id,
            aws_secret_access_key=env_config.aws_secret_access_key
        )

        try:
            # Get secrets
            aws_config = secrets.get_secret('simpla/shared/aws-config')
            queue_names = secrets.get_secret('simpla/shared/queue-names')
            s3_buckets = secrets.get_secret('simpla/shared/s3-buckets')
            service_config = secrets.get_secret('simpla/services/config')
            gemini_keys = secrets.get_secret('simpla/api-keys/gemini')

            # Build AWS credentials
            values['aws'] = {
                'access_key_id': aws_config.get('aws_access_key_id') if env_config.is_localstack else None,
                'secret_access_key': aws_config.get('aws_secret_access_key') if env_config.is_localstack else None,
                'region': aws_config['aws_region']
            }

            # Build SQS config
            if 'sqs' not in values:
                values['sqs'] = {}
            values['sqs']['endpoint'] = aws_config.get('sqs_endpoint') if env_config.is_localstack else None
            values['sqs']['region'] = aws_config['aws_region']
            if 'queues' not in values['sqs']:
                values['sqs']['queues'] = {}
            for queue_type in ['input', 'output']:
                if queue_type in values.get('sqs', {}).get('queues', {}):
                    logical_name = values['sqs']['queues'][queue_type]
                    values['sqs']['queues'][queue_type] = queue_names.get(logical_name, logical_name)

            # Build S3 config
            if 's3' not in values:
                values['s3'] = {}
            values['s3']['bucket_name'] = s3_buckets['processor_bucket']
            values['s3']['endpoint'] = aws_config.get('s3_endpoint') if env_config.is_localstack else None
            values['s3']['region'] = aws_config['aws_region']

            # Add Gemini API key
            if 'gemini' not in values:
                values['gemini'] = {}
            values['gemini']['api_key'] = gemini_keys['api_key']

            # Get service port
            values['port'] = service_config['processor_port']

        except Exception as e:
            print(f"Error loading from Secrets Manager: {e}")
            raise RuntimeError(f"Failed to load configuration. Error: {e}")

        return values


def get_processor_settings() -> Settings:
    """Get application settings instance"""
    return Settings()


# Backwards compatibility aliases
get_settings = get_processor_settings
ProcessorSettings = Settings
