"""S3 cache for processed documents with versioning support"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class ProcessorS3Cache:
    """S3-based cache for processed legal documents with versioning"""

    def __init__(self, bucket_name: str = "processor-cache", endpoint_url: Optional[str] = None):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url

        try:
            if endpoint_url:
                # LocalStack configuration
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id='test',
                    aws_secret_access_key='test',
                    region_name='us-east-1'
                )
            else:
                # Production AWS configuration
                self.s3_client = boto3.client('s3')

            self._ensure_bucket_exists()
            logger.info(f"ProcessorS3Cache initialized with bucket: {bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize S3 cache: {e}")
            self.s3_client = None

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                try:
                    if self.endpoint_url:
                        # LocalStack
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        # AWS
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
                        )
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket {self.bucket_name}: {create_error}")
                    raise

    def _get_cache_key(self, infoleg_id: int, version: str = "latest") -> str:
        """Generate S3 key for cached processed document"""
        return f"processed/{infoleg_id}/{version}.json"

    def _get_metadata_key(self, infoleg_id: int) -> str:
        """Generate S3 key for document metadata"""
        return f"metadata/{infoleg_id}.json"

    def get_cached_processed_data(self, infoleg_id: int, version: str = "latest") -> Optional[Dict[str, Any]]:
        """Retrieve cached processed data for a document"""
        if not self.s3_client:
            return None

        try:
            cache_key = self._get_cache_key(infoleg_id, version)

            # If requesting latest, get the actual latest version
            if version == "latest":
                latest_version = self._get_latest_version(infoleg_id)
                if not latest_version:
                    return None
                cache_key = self._get_cache_key(infoleg_id, latest_version)

            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=cache_key)
            cached_data = json.loads(response['Body'].read().decode('utf-8'))

            logger.info(f"Cache hit for processed document {infoleg_id} (version: {version})")
            return cached_data

        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                logger.error(f"Error retrieving cached processed data for {infoleg_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving cached processed data for {infoleg_id}: {e}")
            return None

    def cache_processed_data(self, infoleg_id: int, processed_data: Dict[str, Any]) -> bool:
        """Cache processed document data with automatic versioning"""
        if not self.s3_client:
            return False

        try:
            # Generate new version
            new_version = self._generate_new_version(infoleg_id)
            cache_key = self._get_cache_key(infoleg_id, new_version)

            # Add caching metadata
            cache_metadata = {
                "cached_at": datetime.now().isoformat(),
                "version": new_version,
                "infoleg_id": infoleg_id
            }
            processed_data["cache_metadata"] = cache_metadata

            # Store in S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=cache_key,
                Body=json.dumps(processed_data, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )

            # Update metadata
            self._update_metadata(infoleg_id, new_version)

            logger.info(f"Cached processed document {infoleg_id} as version {new_version}")
            return True

        except Exception as e:
            logger.error(f"Error caching processed document {infoleg_id}: {e}")
            return False

    def _generate_new_version(self, infoleg_id: int) -> str:
        """Generate new version string for document"""
        latest_version = self._get_latest_version(infoleg_id)

        if not latest_version:
            return "v1"

        # Extract version number and increment
        try:
            version_num = int(latest_version[1:])  # Remove 'v' prefix
            return f"v{version_num + 1}"
        except (ValueError, IndexError):
            # Fallback to timestamp-based versioning
            return f"v{int(datetime.now().timestamp())}"

    def _get_latest_version(self, infoleg_id: int) -> Optional[str]:
        """Get the latest version for a document"""
        try:
            metadata = self._get_metadata(infoleg_id)
            return metadata.get("latest_version") if metadata else None
        except Exception:
            return None

    def _get_metadata(self, infoleg_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a document"""
        try:
            metadata_key = self._get_metadata_key(infoleg_id)
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError:
            return None

    def _update_metadata(self, infoleg_id: int, new_version: str):
        """Update metadata for a document"""
        try:
            metadata = self._get_metadata(infoleg_id) or {
                "infoleg_id": infoleg_id,
                "versions": [],
                "created_at": datetime.now().isoformat()
            }

            metadata["latest_version"] = new_version
            metadata["updated_at"] = datetime.now().isoformat()

            if new_version not in metadata["versions"]:
                metadata["versions"].append(new_version)

            metadata_key = self._get_metadata_key(infoleg_id)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )

        except Exception as e:
            logger.error(f"Error updating metadata for {infoleg_id}: {e}")


    def get_document_versions(self, infoleg_id: int) -> List[str]:
        """Get all available versions for a document"""
        try:
            metadata = self._get_metadata(infoleg_id)
            return metadata.get("versions", []) if metadata else []
        except Exception:
            return []

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        if not self.s3_client:
            return {"error": "S3 client not available"}

        try:
            stats = {
                "total_documents": 0,
                "total_versions": 0,
                "bucket_name": self.bucket_name,
                "documents": {}
            }

            # List all metadata files to get document count
            metadata_prefix = "metadata/"
            paginator = self.s3_client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=metadata_prefix):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    if obj['Key'].endswith('.json'):
                        try:
                            # Extract infoleg_id from key
                            infoleg_id = int(obj['Key'].replace(metadata_prefix, '').replace('.json', ''))
                            metadata = self._get_metadata(infoleg_id)

                            if metadata:
                                versions = metadata.get("versions", [])
                                stats["documents"][infoleg_id] = {
                                    "versions": len(versions),
                                    "latest_version": metadata.get("latest_version"),
                                    "created_at": metadata.get("created_at"),
                                    "updated_at": metadata.get("updated_at")
                                }
                                stats["total_versions"] += len(versions)

                        except (ValueError, KeyError):
                            continue

            stats["total_documents"] = len(stats["documents"])
            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}

    def list_cached_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recently cached documents with their metadata"""
        if not self.s3_client:
            return []

        try:
            documents = []
            metadata_prefix = "metadata/"

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=metadata_prefix,
                MaxKeys=limit
            )

            if 'Contents' not in response:
                return documents

            # Sort by last modified date
            sorted_objects = sorted(
                response['Contents'],
                key=lambda x: x['LastModified'],
                reverse=True
            )

            for obj in sorted_objects[:limit]:
                if obj['Key'].endswith('.json'):
                    try:
                        infoleg_id = int(obj['Key'].replace(metadata_prefix, '').replace('.json', ''))
                        metadata = self._get_metadata(infoleg_id)

                        if metadata:
                            documents.append({
                                "infoleg_id": infoleg_id,
                                "latest_version": metadata.get("latest_version"),
                                "versions_count": len(metadata.get("versions", [])),
                                "created_at": metadata.get("created_at"),
                                "updated_at": metadata.get("updated_at"),
                                "last_modified": obj['LastModified'].isoformat()
                            })

                    except (ValueError, KeyError):
                        continue

            return documents

        except Exception as e:
            logger.error(f"Error listing cached documents: {e}")
            return []

