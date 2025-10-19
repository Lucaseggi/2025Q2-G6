import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# Import shared secrets manager
sys.path.append('/app/shared')
from secrets_manager import SecretsManager


# Nested configuration models for structure
class ServiceConfig(BaseModel):
    """Service configuration (non-sensitive)"""
    name: str = "enhanced-scraper-ms"
    version: str = "2.0.0"
    debug: bool = False


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: Optional[str] = None  # None for AWS Lambda (uses IAM role)
    region: str
    queues: Dict[str, str]  # Actual queue names (not logical)


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
    Application configuration settings with centralized environment detection.

    This class:
    1. Detects environment (LocalStack vs AWS Lambda)
    2. Loads config.json for algorithm parameters
    3. Configures SecretsManager explicitly (no auto-detection)
    4. Provides all configuration to services

    Services never need to access os.getenv() - everything comes from Settings.
    """

    # Environment detection (populated first)
    environment: EnvironmentConfig

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

    @staticmethod
    def _detect_environment() -> EnvironmentConfig:
        """
        Detect if running in LocalStack or AWS Lambda environment.

        This is the ONLY place in the entire codebase that should detect environment.
        All other code receives configuration from Settings.
        """
        # Check for LocalStack indicators
        localstack_indicators = [
            'localstack' in os.getenv('SQS_ENDPOINT', '').lower(),
            'localstack' in os.getenv('S3_ENDPOINT', '').lower(),
            'localstack' in os.getenv('SECRETS_MANAGER_ENDPOINT', '').lower(),
            os.getenv('USE_LOCALSTACK', '').lower() == 'true',
            os.getenv('AWS_ACCESS_KEY_ID') == 'test'
        ]
        is_localstack = any(localstack_indicators)

        # Check for Lambda environment
        is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ and not is_localstack

        # Build environment config
        env_config = {
            'is_localstack': is_localstack,
            'is_lambda': is_lambda,
            'aws_region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }

        # LocalStack: explicit credentials and endpoints
        if is_localstack:
            env_config['secrets_manager_endpoint'] = os.getenv('SECRETS_MANAGER_ENDPOINT', 'http://localstack:4566')
            env_config['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID', 'test')
            env_config['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        # Lambda: IAM role, no credentials needed
        else:
            env_config['secrets_manager_endpoint'] = None
            env_config['aws_access_key_id'] = None
            env_config['aws_secret_access_key'] = None

        return EnvironmentConfig(**env_config)

    @model_validator(mode='before')
    def load_config(cls, values):
        """Load configuration from environment detection + config.json + Secrets Manager"""

        # STEP 1: Detect environment (FIRST THING - owns all environment logic)
        env_config = cls._detect_environment()
        values['environment'] = env_config.model_dump()

        # STEP 2: Load algorithm parameters from config.json
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path) as f:
                json_config = json.load(f)

            # Merge JSON config (non-sensitive params)
            for key, value in json_config.items():
                if key not in values:
                    values[key] = value

        # STEP 3: Load sensitive data from AWS Secrets Manager
        # Initialize SecretsManager with explicit configuration (no auto-detection)
        secrets = SecretsManager(
            endpoint_url=env_config.secrets_manager_endpoint,
            region_name=env_config.aws_region,
            aws_access_key_id=env_config.aws_access_key_id,
            aws_secret_access_key=env_config.aws_secret_access_key
        )

        try:
            # Get AWS config
            aws_config = secrets.get_secret('simpla/shared/aws-config')

            # Get queue names
            queue_names = secrets.get_secret('simpla/shared/queue-names')

            # Get S3 buckets
            s3_buckets = secrets.get_secret('simpla/shared/s3-buckets')

            # Get service config
            service_config = secrets.get_secret('simpla/services/config')

            # Build AWS credentials config
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
            if 'output' in values.get('sqs', {}).get('queues', {}):
                logical_name = values['sqs']['queues']['output']
                values['sqs']['queues']['output'] = queue_names.get(logical_name, logical_name)

            # Build S3 config
            if 's3' not in values:
                values['s3'] = {}
            values['s3']['bucket_name'] = s3_buckets['scraper_bucket']
            values['s3']['endpoint'] = aws_config.get('s3_endpoint') if env_config.is_localstack else None
            values['s3']['region'] = aws_config['aws_region']

            # Get service port
            values['port'] = service_config['scraper_port']

        except Exception as e:
            print(f"Error loading from Secrets Manager: {e}")
            raise RuntimeError(
                f"Failed to load configuration from Secrets Manager. "
                f"Ensure secrets are properly configured. Error: {e}"
            )

        return values


def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()