"""Configuration settings for the embedding service with Secrets Manager support"""

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
    name: str = "embedding-ms"
    version: str = "2.0.0"
    debug: bool = False


class SQSQueues(BaseModel):
    """SQS queue names (actual)"""
    input: str
    output: str


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: Optional[str] = None  # None for AWS Lambda
    region: str
    queues: SQSQueues


class AWSCredentials(BaseModel):
    """AWS credentials (empty for Lambda, populated for LocalStack)"""
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: str


class EmbeddingConfig(BaseModel):
    """Embedding configuration"""
    embedding_model_name: str
    output_dimensionality: int
    provider: str
    max_retries: int = 5
    api_key: str  # From secrets


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
    aws: AWSCredentials
    embedding: EmbeddingConfig

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
        possible_paths = [
            Path(__file__).parent.parent.parent / "config.json",
            Path.cwd() / "config.json",
            Path("config.json")
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if config_path:
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

            # Map logical queue names to actual queue names
            if 'queues' in values.get('sqs', {}):
                sqs_queues = values['sqs']['queues']
                mapped_queues = {}
                for queue_type, logical_name in sqs_queues.items():
                    mapped_queues[queue_type] = queue_names.get(logical_name, logical_name)
                values['sqs']['queues'] = mapped_queues

            # Add Gemini API key
            if 'embedding' not in values:
                values['embedding'] = {}
            values['embedding']['api_key'] = gemini_keys['api_key']

            # Get service port
            values['port'] = service_config['embedder_port']

        except Exception as e:
            print(f"Error loading from Secrets Manager: {e}")
            raise RuntimeError(f"Failed to load configuration. Error: {e}")

        return values


def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()
