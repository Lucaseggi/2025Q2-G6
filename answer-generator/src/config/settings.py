"""Settings and configuration for the answer generator service"""

import os
import sys
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional

# Import shared secrets manager
sys.path.append('/app/shared')
from secrets_manager import SecretsManager


class EnvironmentConfig:
    """Helper for environment detection"""

    @staticmethod
    def detect():
        """Detect environment (LocalStack vs Lambda)"""
        localstack_indicators = [
            'localstack' in os.getenv('SECRETS_MANAGER_ENDPOINT', '').lower(),
            os.getenv('USE_LOCALSTACK', '').lower() == 'true',
            os.getenv('AWS_ACCESS_KEY_ID') == 'test'
        ]
        is_localstack = any(localstack_indicators)
        is_lambda = 'AWS_LAMBDA_FUNCTION_NAME' in os.environ and not is_localstack

        return {
            'is_localstack': is_localstack,
            'is_lambda': is_lambda,
            'aws_region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            'secrets_manager_endpoint': os.getenv('SECRETS_MANAGER_ENDPOINT', 'http://localstack:4566') if is_localstack else None,
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test') if is_localstack else None,
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test') if is_localstack else None
        }


class Settings(BaseSettings):
    """Service configuration"""

    # Service settings
    service_name: str = "answer-generator"
    service_port: int = 8042
    service_host: str = "0.0.0.0"
    debug: bool = False

    # External service URLs
    embedder_api_host: str = "http://embedder-api:8001"
    vectorial_api_host: str = "http://vectorial-guard:8080"
    relational_api_host: str = "http://relational-guard:8090"

    # RAG settings
    default_search_limit: int = 5

    # LLM settings
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash-lite"
    gemini_max_retries: int = 3

    model_config = {
        "case_sensitive": False,
        "extra": "ignore"
    }

    @model_validator(mode='before')
    @classmethod
    def load_secrets(cls, values):
        """Load configuration from environment and Secrets Manager"""

        # STEP 1: Detect environment
        env_config = EnvironmentConfig.detect()

        # STEP 2: Override with environment variables if present
        if os.getenv('SERVICE_PORT'):
            values['service_port'] = int(os.getenv('SERVICE_PORT'))
        if os.getenv('SERVICE_HOST'):
            values['service_host'] = os.getenv('SERVICE_HOST')
        if os.getenv('DEBUG'):
            values['debug'] = os.getenv('DEBUG', '0') == '1'
        if os.getenv('EMBEDDER_API_HOST'):
            values['embedder_api_host'] = os.getenv('EMBEDDER_API_HOST')
        if os.getenv('VECTORIAL_API_HOST'):
            values['vectorial_api_host'] = os.getenv('VECTORIAL_API_HOST')
        if os.getenv('RELATIONAL_API_HOST'):
            values['relational_api_host'] = os.getenv('RELATIONAL_API_HOST')
        if os.getenv('DEFAULT_SEARCH_LIMIT'):
            values['default_search_limit'] = int(os.getenv('DEFAULT_SEARCH_LIMIT'))

        # STEP 3: Load Gemini API key from Secrets Manager
        try:
            secrets = SecretsManager(
                endpoint_url=env_config['secrets_manager_endpoint'],
                region_name=env_config['aws_region'],
                aws_access_key_id=env_config['aws_access_key_id'],
                aws_secret_access_key=env_config['aws_secret_access_key']
            )

            gemini_keys = secrets.get_secret('simpla/api-keys/gemini')
            values['gemini_api_key'] = gemini_keys.get('api_key')

            if values['gemini_api_key']:
                print(f"Successfully loaded Gemini API key from Secrets Manager")
            else:
                print("Warning: Gemini API key not found in secrets")

        except Exception as e:
            print(f"Warning: Could not load secrets from Secrets Manager: {e}")
            # Fallback to environment variable
            values['gemini_api_key'] = os.getenv('GEMINI_API_KEY')
            if values['gemini_api_key']:
                print("Using Gemini API key from environment variable")
            else:
                print("Warning: No Gemini API key available")

        return values


# Singleton settings instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
