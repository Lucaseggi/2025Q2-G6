import os
import json
import boto3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class S3Cache:
    def __init__(self):
        """Initialize S3 cache client"""
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'simpla-cache')
        self.s3_endpoint = os.getenv('S3_ENDPOINT')

        # Configure S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
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

    def _get_cache_key(self, norma_id: int) -> str:
        """Generate cache key for a norma"""
        return f"normas/{norma_id}.json"

    def get_cached_norma(self, norma_id: int) -> Optional[Dict[str, Any]]:
        """Get cached norma data from S3"""
        cache_key = self._get_cache_key(norma_id)

        try:
            logger.info(f"Checking S3 cache for norma {norma_id}")
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=cache_key
            )

            content = response['Body'].read().decode('utf-8')
            cached_data = json.loads(content)

            logger.info(f"Found cached norma {norma_id} in S3")
            return cached_data

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.info(f"Norma {norma_id} not found in cache")
                return None
            else:
                logger.error(f"Error retrieving cached norma {norma_id}: {e}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving cached norma {norma_id}: {e}")
            return None

    def cache_norma(self, norma_id: int, norma_data: Dict[str, Any]) -> bool:
        """Cache norma data in S3"""
        cache_key = self._get_cache_key(norma_id)

        try:
            # Add cache metadata
            cache_data = {
                "norma_id": norma_id,
                "cached_at": datetime.now().isoformat(),
                "cache_version": "1.0",
                "data": norma_data
            }

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=cache_key,
                Body=json.dumps(cache_data, indent=2),
                ContentType='application/json',
                Metadata={
                    'norma_id': str(norma_id),
                    'cached_at': datetime.now().isoformat()
                }
            )

            logger.info(f"Successfully cached norma {norma_id} in S3")
            return True

        except Exception as e:
            logger.error(f"Error caching norma {norma_id}: {e}")
            return False

    def is_cached(self, norma_id: int) -> bool:
        """Check if norma exists in cache without retrieving data"""
        cache_key = self._get_cache_key(norma_id)

        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=cache_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            else:
                logger.error(f"Error checking cache for norma {norma_id}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking cache for norma {norma_id}: {e}")
            return False

    def delete_cached_norma(self, norma_id: int) -> bool:
        """Delete cached norma from S3"""
        cache_key = self._get_cache_key(norma_id)

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=cache_key
            )
            logger.info(f"Deleted cached norma {norma_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cached norma {norma_id}: {e}")
            return False

    def list_cached_normas(self, limit: int = 100) -> list:
        """List cached norma IDs"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='normas/',
                MaxKeys=limit
            )

            norma_ids = []
            for obj in response.get('Contents', []):
                # Extract norma ID from key like 'normas/183532.json'
                key = obj['Key']
                if key.startswith('normas/') and key.endswith('.json'):
                    norma_id = key.replace('normas/', '').replace('.json', '')
                    try:
                        norma_ids.append(int(norma_id))
                    except ValueError:
                        continue

            return sorted(norma_ids)

        except Exception as e:
            logger.error(f"Error listing cached normas: {e}")
            return []

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='normas/'
            )

            total_objects = response.get('KeyCount', 0)
            total_size = sum(obj.get('Size', 0) for obj in response.get('Contents', []))

            return {
                "total_cached_normas": total_objects,
                "total_cache_size_bytes": total_size,
                "bucket_name": self.bucket_name,
                "s3_endpoint": self.s3_endpoint
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "error": str(e),
                "bucket_name": self.bucket_name,
                "s3_endpoint": self.s3_endpoint
            }