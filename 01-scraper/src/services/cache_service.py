import boto3
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError

from ..interfaces.cache_interface import CacheInterface
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class CacheService(CacheInterface):
    """S3-based cache service implementation"""

    def __init__(self, settings: Settings):
        """Initialize cache service with S3 backend"""
        self.bucket_name = settings.s3.bucket_name
        self.s3_endpoint = settings.s3.endpoint

        # Configure S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=settings.aws.access_key_id,
            aws_secret_access_key=settings.aws.secret_access_key,
            region_name=settings.aws.region
        )

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

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache by key"""
        try:
            logger.debug(f"Retrieving from cache: {key}")
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            content = response['Body'].read().decode('utf-8')
            cached_data = json.loads(content)

            logger.debug(f"Found cached data for key: {key}")
            return cached_data

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.debug(f"Key not found in cache: {key}")
                return None
            else:
                logger.error(f"Error retrieving from cache {key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving from cache {key}: {e}")
            return None

    def put(self, key: str, data: Dict[str, Any]) -> bool:
        """Store data in cache with the given key (overwrites if exists)"""
        try:
            # Add cache metadata
            cache_data = {
                "cached_at": datetime.now().isoformat(),
                "cache_version": "1.0",
                "data": data
            }

            # Upload to S3 (overwrites existing)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(cache_data, indent=2),
                ContentType='application/json',
                Metadata={
                    'cached_at': datetime.now().isoformat()
                }
            )

            logger.debug(f"Successfully cached data for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Error caching data for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache without retrieving data"""
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
                logger.error(f"Error checking cache for key {key}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking cache for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete data from cache by key"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.debug(f"Deleted cached data for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cached data for key {key}: {e}")
            return False