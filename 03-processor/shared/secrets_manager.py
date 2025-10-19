"""
AWS Secrets Manager integration for Simpla pipeline.

Simple client configured explicitly by Settings. No auto-detection.
Settings handles all environment detection and passes config here.
"""

import json
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError


class SecretsManager:
    """
    Simple Secrets Manager client configured explicitly by Settings.

    No auto-detection - receives all configuration from Settings.

    Usage:
        # Settings creates and configures this
        secrets = SecretsManager(
            endpoint_url='http://localstack:4566',  # or None for AWS
            region_name='us-east-1',
            aws_access_key_id='test',  # or None for Lambda IAM role
            aws_secret_access_key='test'  # or None for Lambda IAM role
        )
        aws_config = secrets.get_secret('simpla/shared/aws-config')
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        region_name: str = 'us-east-1',
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize Secrets Manager client with explicit configuration.

        All parameters come from Settings - no environment detection here.

        Args:
            endpoint_url: SecretsManager endpoint (for LocalStack). None for AWS.
            region_name: AWS region
            aws_access_key_id: AWS access key (for LocalStack). None for Lambda IAM role.
            aws_secret_access_key: AWS secret key (for LocalStack). None for Lambda IAM role.
        """
        # Build client configuration
        client_config = {
            'region_name': region_name
        }

        # Add endpoint if provided (LocalStack)
        if endpoint_url:
            client_config['endpoint_url'] = endpoint_url

        # Add credentials if provided (LocalStack); omit for Lambda IAM role
        if aws_access_key_id and aws_secret_access_key:
            client_config['aws_access_key_id'] = aws_access_key_id
            client_config['aws_secret_access_key'] = aws_secret_access_key

        self.client = boto3.client('secretsmanager', **client_config)

    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve secret from AWS Secrets Manager.

        Falls back to environment variables if Secrets Manager is unavailable.
        This fallback is mainly for local development and Docker Compose.

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

        sqs_endpoint = aws_config.get('sqs_endpoint', '')
        actual_queue_name = queue_names.get(queue_name, queue_name)

        # LocalStack format: http://endpoint/account_id/queue_name
        if sqs_endpoint and 'localstack' in sqs_endpoint:
            return f"{sqs_endpoint}/000000000000/{actual_queue_name}"

        # Real AWS format - construct from region
        region = aws_config['aws_region']
        # In Lambda, get account ID from execution role via environment
        # This is one of the few cases where env access is acceptable
        account_id = os.getenv('AWS_ACCOUNT_ID', '000000000000')
        return f"https://sqs.{region}.amazonaws.com/{account_id}/{actual_queue_name}"
