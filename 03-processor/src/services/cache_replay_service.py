"""Cache replay service for processor"""

import logging
import sys
import os
from typing import Tuple, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from sqs_client import SQSClient

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from ..config.settings import Settings

from ..interfaces.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


class CacheReplayService:
    """Service for replaying cached processor results to embedding queue"""

    def __init__(self, storage_service: StorageInterface, settings: Settings):
        """Initialize cache replay service"""
        self.storage = storage_service
        self.settings = settings

        # Set SQS environment variables for shared SQS client
        if self.settings.sqs.endpoint:
            os.environ['SQS_ENDPOINT'] = self.settings.sqs.endpoint
        os.environ['AWS_DEFAULT_REGION'] = self.settings.sqs.region

        self.queue_client = SQSClient()

    def _get_cache_key(self, norm_id: int) -> str:
        """Generate cache key for a processed norm"""
        return f"processed_norms/{norm_id}.json"

    def replay_norm(self, norm_id: int, force: bool = False) -> Tuple[bool, str]:
        """Replay a norm from cache to embedding queue"""
        logger.info(f"Replaying norm {norm_id} (force={force})")

        cache_key = self._get_cache_key(norm_id)

        # Get from cache
        cached_data = self.storage.get(cache_key)
        if not cached_data:
            logger.error(f"Norm {norm_id} not found in cache")
            return False, "not_in_cache"

        # Send to embedding queue
        success = self.queue_client.send_message(
            self.settings.sqs.queues['output'],
            cached_data
        )

        if success:
            logger.info(f"Successfully replayed norm {norm_id} to embedding queue")
            return True, "replayed"
        else:
            logger.error(f"Failed to replay norm {norm_id}")
            return False, "queue_failed"

    def is_cached(self, norm_id: int) -> bool:
        """Check if a norm is cached"""
        cache_key = self._get_cache_key(norm_id)
        return self.storage.exists(cache_key)
