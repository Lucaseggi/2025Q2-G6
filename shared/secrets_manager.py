"""
AWS Secrets Manager integration for Simpla pipeline.

Provides centralized secret management with fallback to environment variables
for local development. Supports both real AWS and LocalStack.
"""

import json
import os
from typing import Dict, Any, Optional
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError


class SecretsManager:
    """
    Manages secrets from AWS Secrets Manager with environment variable fallback.

    Usage:
        secrets = SecretsManager()
        aws_config = secrets.get_secret('simpla/shared/aws-config')
        region = aws_config['aws_region']
    """

    def __init__(self, use_localstack: Optional[bool] = None):
        """
        Initialize Secrets Manager client.

        Args:
            use_localstack: Force LocalStack mode. If None, auto-detects from environment.
        """
        # Auto-detect LocalStack if not specified
        if use_localstack is None:
            use_localstack = self._is_localstack_env()

        self.use_localstack = use_localstack

        # Initialize boto3 client
        if use_localstack:
            # LocalStack configuration
            endpoint_url = os.getenv('SECRETS_MANAGER_ENDPOINT', 'http://localstack:4566')
            self.client = boto3.client(
                'secretsmanager',
                endpoint_url=endpoint_url,
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
            )
        else:
            # Real AWS configuration (uses instance role in Lambda)
            self.client = boto3.client(
                'secretsmanager',
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )

    @staticmethod
    def _is_localstack_env() -> bool:
        """Detect if running in LocalStack environment."""
        # Check for LocalStack-specific environment variables
        localstack_indicators = [
            os.getenv('SQS_ENDPOINT', '').find('localstack') != -1,
            os.getenv('S3_ENDPOINT', '').find('localstack') != -1,
            os.getenv('SECRETS_MANAGER_ENDPOINT', '').find('localstack') != -1,
            os.getenv('USE_LOCALSTACK', '').lower() == 'true',
            os.getenv('AWS_ACCESS_KEY_ID') == 'test'
        ]
        return any(localstack_indicators)

    @lru_cache(maxsize=32)
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve secret from AWS Secrets Manager with caching.

        Falls back to environment variables if Secrets Manager is unavailable.

        Args:
            secret_name: Name of the secret (e.g., 'simpla/shared/aws-config')

        Returns:
            Dictionary containing secret values

        Raises:
            ValueError: If secret not found and no environment fallback available
        """
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except ClientError as e:
            error_code = e.response['Error']['Code']

            # If secret doesn't exist, try environment variable fallback
            if error_code in ['ResourceNotFoundException', 'SecretNotFound']:
                return self._get_from_env_fallback(secret_name)

            # For other errors (access denied, network), also try fallback
            return self._get_from_env_fallback(secret_name)
        except Exception:
            # If boto3 fails entirely (no AWS SDK, network issues), use env vars
            return self._get_from_env_fallback(secret_name)

    def _get_from_env_fallback(self, secret_name: str) -> Dict[str, Any]:
        """
        Fallback to environment variables when Secrets Manager is unavailable.

        Maps secret names to environment variable schemas.
        """
        fallback_mappings = {
            'simpla/shared/aws-config': {
                'aws_region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                'sqs_endpoint': os.getenv('SQS_ENDPOINT', 'http://localstack:4566'),
                's3_endpoint': os.getenv('S3_ENDPOINT', 'http://localstack:4566'),
                'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
            },
            'simpla/shared/queue-names': {
                'purifying': os.getenv('PURIFYING_QUEUE_NAME', 'purifying'),
                'processing': os.getenv('PROCESSING_QUEUE_NAME', 'processing'),
                'embedding': os.getenv('EMBEDDING_QUEUE_NAME', 'embedding'),
                'inserting': os.getenv('INSERTING_QUEUE_NAME', 'inserting')
            },
            'simpla/shared/s3-buckets': {
                'scraper_bucket': os.getenv('SCRAPER_BUCKET', 'simpla-scraper-storage'),
                'purifier_bucket': os.getenv('PURIFIER_BUCKET', 'simpla-purifier-storage'),
                'processor_bucket': os.getenv('PROCESSOR_BUCKET', 'simpla-processor-storage')
            },
            'simpla/api-keys/gemini': {
                'api_key': os.getenv('GEMINI_API_KEY', os.getenv('GEMINI_API_KEY_1', ''))
            },
            'simpla/services/config': {
                'opensearch_endpoint': os.getenv('OPENSEARCH_ENDPOINT', 'http://opensearch:9200'),
                'scraper_port': int(os.getenv('SCRAPER_PORT', '8003')),
                'purifier_port': int(os.getenv('PURIFIER_PORT', '8004')),
                'processor_port': int(os.getenv('PROCESSOR_PORT', '8005')),
                'embedder_port': int(os.getenv('EMBEDDER_PORT', '8001')),
                'inserter_storage_client_type': os.getenv('STORAGE_CLIENT_TYPE', 'rest')
            }
        }

        if secret_name not in fallback_mappings:
            raise ValueError(
                f"Secret '{secret_name}' not found in Secrets Manager and no "
                f"environment variable fallback defined"
            )

        return fallback_mappings[secret_name]

    def get_queue_url(self, queue_name: str) -> str:
        """
        Build full SQS queue URL from configuration.

        Args:
            queue_name: Logical queue name (e.g., 'purifying', 'processing')

        Returns:
            Full queue URL (e.g., 'http://localstack:4566/000000000000/purifying')
        """
        aws_config = self.get_secret('simpla/shared/aws-config')
        queue_names = self.get_secret('simpla/shared/queue-names')

        sqs_endpoint = aws_config['sqs_endpoint']
        actual_queue_name = queue_names.get(queue_name, queue_name)

        # LocalStack format: http://endpoint/account_id/queue_name
        if 'localstack' in sqs_endpoint:
            return f"{sqs_endpoint}/000000000000/{actual_queue_name}"

        # Real AWS format - construct from region
        region = aws_config['aws_region']
        # In Lambda, get account ID from execution role
        # For now, use environment variable or default
        account_id = os.getenv('AWS_ACCOUNT_ID', '000000000000')
        return f"https://sqs.{region}.amazonaws.com/{account_id}/{actual_queue_name}"


# Global singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get global SecretsManager instance (singleton pattern).

    Returns:
        Shared SecretsManager instance
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
