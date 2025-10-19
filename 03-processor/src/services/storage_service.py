"""S3-based storage service implementation for processor"""

import boto3
import json
import logging
from typing import Dict, Any
from botocore.exceptions import ClientError

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from interfaces.storage_interface import StorageInterface
from config.settings import Settings

logger = logging.getLogger(__name__)


class StorageService(StorageInterface):
    """S3-based storage service implementation"""

    def __init__(self, settings: Settings):
        """Initialize storage service with S3 backend"""
        self.bucket_name = settings.s3.bucket_name
        self.s3_endpoint = settings.s3.endpoint

        # Build S3 client configuration from settings
        client_config = {
            'region_name': settings.aws.region
        }

        # Only add endpoint if provided (LocalStack)
        if self.s3_endpoint:
            client_config['endpoint_url'] = self.s3_endpoint

        # Only add credentials if provided (LocalStack); Lambda uses IAM role
        if settings.aws.access_key_id and settings.aws.secret_access_key:
            client_config['aws_access_key_id'] = settings.aws.access_key_id
            client_config['aws_secret_access_key'] = settings.aws.secret_access_key

        self.s3_client = boto3.client('s3', **client_config)

        # Initialize bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> bool:
        """Ensure the S3 bucket exists, create if it doesn't"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' exists")
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket '{self.bucket_name}': {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket '{self.bucket_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error with S3 bucket: {e}")
            return False

    def store(self, key: str, data: Dict[str, Any]) -> bool:
        """Store data with the given key (overwrites if exists)"""
        try:
            # Upload to S3 (overwrites existing)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(data, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )

            logger.debug(f"Successfully stored data for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Error storing data for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in storage without retrieving data"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            else:
                logger.error(f"Error checking storage for key {key}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking storage for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete data from storage by key"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.debug(f"Deleted stored data for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting stored data for key {key}: {e}")
            return False

    def get(self, key: str) -> Dict[str, Any]:
        """Retrieve data from storage by key"""
        try:
            logger.debug(f"Retrieving from storage: {key}")
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            logger.debug(f"Found data for key: {key}")
            return data

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.debug(f"Key not found in storage: {key}")
                return None
            else:
                logger.error(f"Error retrieving from storage {key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving from storage {key}: {e}")
            return None

    def store_failed_processing(self, infoleg_id: int, failed_data: Dict[str, Any]) -> bool:
        """Store failed processing data for later analysis"""
        try:
            key = f"failed_norms/{infoleg_id}.json"

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(failed_data, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )

            logger.info(f"Stored failed processing data for norm {infoleg_id} in S3")
            return True

        except Exception as e:
            logger.error(f"Error storing failed processing data for norm {infoleg_id}: {e}")
            return False
