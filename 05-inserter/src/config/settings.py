"""Configuration management for inserter service using Pydantic with Secrets Manager"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings

# Import shared secrets manager
sys.path.append('/var/task/shared')
sys.path.append('/app/shared')
from secrets_manager import SecretsManager


class ServiceConfig(BaseModel):
    """Service configuration (non-sensitive)"""
    name: str = "inserter-ms"
    version: str = "2.0.0"
    debug: bool = False


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: Optional[str] = None  # None for AWS Lambda
    region: str
    queues: Dict[str, str]  # Actual queue names


class AWSCredentials(BaseModel):
    """AWS credentials (empty for Lambda, populated for LocalStack)"""
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: str


class StorageConfig(BaseModel):
    """Storage configuration (algorithm parameters from config.json)"""
    default_client_type: str
    timeout_seconds: int
    max_retries: int
    retry_delay_seconds: int


class ApiEndpointsConfig(BaseModel):
    """API endpoint configuration for guard services"""
    relational_api_url: str
    vectorial_api_url: str


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
    storage: StorageConfig
    api_endpoints: ApiEndpointsConfig

    # Service-specific runtime config
    opensearch_endpoint: str
    port: int = Field(ge=1, le=65535, default=8005)

    model_config = {
        "case_sensitive": False,
        "extra": "ignore"
    }

    @staticmethod
    def _detect_environment() -> EnvironmentConfig:
        """Detect environment (LocalStack vs Lambda). ONLY place with env detection."""
        localstack_indicators = [
            'localstack' in os.getenv('SQS_ENDPOINT', '').lower(),
            'localstack' in os.getenv('OPENSEARCH_ENDPOINT', '').lower(),
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
            Path("/var/task/config.json"),  # Lambda
            Path("/app/config.json"),  # Docker
            Path.cwd() / "config.json",  # Current working directory
            Path(__file__).parent.parent.parent / "config.json"
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
        else:
            # Use minimal defaults if config.json not found
            json_config = {
                'service': {'name': 'inserter-ms', 'version': '2.0.0', 'debug': False},
                'storage': {'default_client_type': 'rest', 'timeout_seconds': 30, 'max_retries': 3, 'retry_delay_seconds': 1},
                'sqs': {'queues': {'input': 'inserting'}}
            }
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
            guard_endpoints = secrets.get_secret('simpla/services/guard-endpoints')

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
            # Map logical queue name to actual queue name
            logical_name = values['sqs']['queues'].get('input', 'inserting')
            values['sqs']['queues']['input'] = queue_names.get(logical_name, logical_name)

            # Build API endpoints config
            values['api_endpoints'] = {
                'relational_api_url': guard_endpoints['relational_api_url'],
                'vectorial_api_url': guard_endpoints['vectorial_api_url']
            }

            # Get opensearch endpoint
            values['opensearch_endpoint'] = service_config['opensearch_endpoint']

            # Get service port
            values['port'] = service_config.get('inserter_port', 8005)

        except Exception as e:
            print(f"Error loading from Secrets Manager: {e}")
            raise RuntimeError(f"Failed to load configuration. Error: {e}")

        return values


def get_inserter_settings() -> Settings:
    """Get application settings instance"""
    return Settings()


# Backwards compatibility aliases
get_settings = get_inserter_settings
InserterSettings = Settings
