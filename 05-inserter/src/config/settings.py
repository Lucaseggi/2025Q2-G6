"""Configuration settings for the inserter service with Secrets Manager support"""

import json
import os
import sys
from pathlib import Path
from functools import lru_cache
from typing import Dict
from pydantic import BaseModel, Field


# Import shared secrets manager
sys.path.append('/app/shared')
from secrets_manager import get_secrets_manager


class ServiceConfig(BaseModel):
    """Service configuration (non-sensitive)"""
    name: str = "inserter-ms"
    version: str = "2.0.0"
    debug: bool = False


class SQSQueues(BaseModel):
    """SQS queue names (logical)"""
    input: str


class SQSConfig(BaseModel):
    """SQS configuration"""
    endpoint: str  # From secrets
    region: str  # From secrets
    queues: SQSQueues


class AWSCredentials(BaseModel):
    """AWS credentials (from secrets)"""
    access_key_id: str
    secret_access_key: str
    region: str


class StorageConfig(BaseModel):
    """Storage configuration (algorithm parameters from config.json)"""
    default_client_type: str
    timeout_seconds: int
    max_retries: int
    retry_delay_seconds: int


class GrpcServiceConfig(BaseModel):
    """gRPC service configuration"""
    timeout_seconds: int


class GrpcConfig(BaseModel):
    """gRPC configuration (algorithm parameters from config.json)"""
    relational_service: GrpcServiceConfig
    vectorial_service: GrpcServiceConfig


class Settings(BaseModel):
    """Application configuration settings"""
    service: ServiceConfig
    sqs: SQSConfig
    aws: AWSCredentials
    storage: StorageConfig
    grpc: GrpcConfig

    # Service runtime config from secrets
    opensearch_endpoint: str
    relational_host: str = "relational-guard"
    relational_port: int = 50051
    vectorial_host: str = "vectorial-guard"
    vectorial_port: int = 50052


def load_config() -> Settings:
    """Load configuration from config.json and AWS Secrets Manager"""
    # 1. Load algorithm parameters from config.json
    possible_paths = [
        Path(__file__).parent.parent.parent / "config.json",  # /app/config.json
        Path.cwd() / "config.json",  # Current working directory
        Path("config.json")  # Relative
    ]

    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            break

    if not config_path:
        raise FileNotFoundError(f"Could not find config.json in any of: {possible_paths}")

    with open(config_path, 'r') as f:
        json_config = json.load(f)

    # 2. Load sensitive data from AWS Secrets Manager
    try:
        secrets = get_secrets_manager()

        # Get AWS config
        aws_config = secrets.get_secret('simpla/shared/aws-config')
        aws_credentials = {
            'access_key_id': aws_config['aws_access_key_id'],
            'secret_access_key': aws_config['aws_secret_access_key'],
            'region': aws_config['aws_region']
        }

        # Get queue names
        queue_names = secrets.get_secret('simpla/shared/queue-names')

        # Get service config
        service_config = secrets.get_secret('simpla/services/config')

        # Build SQS config
        sqs_queues = json_config.get('sqs', {}).get('queues', {})
        # Map logical queue names to actual queue names
        mapped_queues = {}
        for queue_type, logical_name in sqs_queues.items():
            mapped_queues[queue_type] = queue_names.get(logical_name, logical_name)

        sqs_config = {
            'endpoint': aws_config['sqs_endpoint'],
            'region': aws_config['aws_region'],
            'queues': mapped_queues
        }

        # Build final config
        config_data = {
            'service': json_config.get('service', {}),
            'sqs': sqs_config,
            'aws': aws_credentials,
            'storage': json_config.get('storage', {}),
            'grpc': json_config.get('grpc', {}),
            'opensearch_endpoint': service_config['opensearch_endpoint'],
            # gRPC hosts and ports could be in secrets too, but using defaults for now
            'relational_host': os.getenv('RELATIONAL_MS_HOST', 'relational-guard'),
            'relational_port': int(os.getenv('RELATIONAL_MS_PORT', '50051')),
            'vectorial_host': os.getenv('VECTORIAL_MS_HOST', 'vectorial-guard'),
            'vectorial_port': int(os.getenv('VECTORIAL_MS_PORT', '50052'))
        }

        return Settings(**config_data)

    except Exception as e:
        # Fallback: use environment variables
        print(f"Warning: Could not load from Secrets Manager, using env fallback: {e}")

        # Build from env vars
        sqs_queues = json_config.get('sqs', {}).get('queues', {})
        sqs_config = {
            'endpoint': os.getenv('SQS_ENDPOINT', 'http://localstack:4566'),
            'region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            'queues': sqs_queues
        }

        aws_credentials = {
            'access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            'region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }

        config_data = {
            'service': json_config.get('service', {}),
            'sqs': sqs_config,
            'aws': aws_credentials,
            'storage': json_config.get('storage', {}),
            'grpc': json_config.get('grpc', {}),
            'opensearch_endpoint': os.getenv('OPENSEARCH_ENDPOINT', 'http://opensearch:9200'),
            'relational_host': os.getenv('RELATIONAL_MS_HOST', 'relational-guard'),
            'relational_port': int(os.getenv('RELATIONAL_MS_PORT', '50051')),
            'vectorial_host': os.getenv('VECTORIAL_MS_HOST', 'vectorial-guard'),
            'vectorial_port': int(os.getenv('VECTORIAL_MS_PORT', '50052'))
        }

        return Settings(**config_data)


@lru_cache()
def get_settings() -> Settings:
    """Get cached configuration settings"""
    return load_config()
