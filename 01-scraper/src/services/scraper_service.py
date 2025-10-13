import sys
import os
import time
from datetime import datetime
from typing import Tuple

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import ProcessedData, ScrapingData, ScraperMetadata
from rabbitmq_client import RabbitMQClient
from structured_logger import StructuredLogger, LogStage

from ..interfaces.scraper_interface import ScraperInterface
from ..interfaces.cache_interface import CacheInterface
from ..interfaces.queue_interface import QueueInterface
from ..interfaces.norm_provider_interface import NormProviderInterface

logger = StructuredLogger("scraper", "api")


class ScraperService(ScraperInterface):
    """Scraper service implementation with dependency injection"""

    def __init__(
        self,
        cache_service: CacheInterface,
        queue_service: QueueInterface,
        norm_provider: NormProviderInterface
    ):
        """Initialize scraper service with injected dependencies"""
        self.cache = cache_service
        self.queue = queue_service
        self.norm_provider = norm_provider

    def _get_norm_cache_key(self, norm_id: int) -> str:
        """Generate cache key for a norm"""
        return f"norms/{norm_id}.json"

    def scrape_specific_norm(self, norm_id: int, force: bool = False) -> Tuple[bool, str]:
        """Scrape a specific norm by its ID with caching support"""
        start_time = time.time()

        logger.log_processing_start(
            infoleg_id=norm_id,
            force=force
        )

        cache_key = self._get_norm_cache_key(norm_id)

        # Check cache first (unless force is True)
        if not force:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.log_cache_hit(infoleg_id=norm_id)

                # Mark as from cache and update timestamp
                if 'scraping_data' in cached_data and 'scraper_metadata' in cached_data['scraping_data']:
                    cached_data['scraping_data']['scraper_metadata']['from_cache'] = True
                    cached_data['scraping_data']['scraper_metadata']['scraping_timestamp'] = datetime.now().isoformat()

                # Send to queue
                success = self.queue.send_message('purifying', cached_data)
                if success:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.log_message_sent(
                        queue_name='purifying',
                        infoleg_id=norm_id,
                        from_cache=True
                    )
                    logger.log_processing_complete(
                        infoleg_id=norm_id,
                        duration_ms=duration_ms,
                        source="cache"
                    )
                    return True, "cache"
                else:
                    logger.error(
                        "Failed to send cached norm to queue",
                        stage=LogStage.QUEUE_ERROR,
                        infoleg_id=norm_id
                    )
                    return False, "cache_send_failed"
            else:
                logger.log_cache_miss(infoleg_id=norm_id)

        # If not in cache or force=True, scrape from data source
        try:
            logger.info(
                "Fetching norm from InfoLeg API",
                stage=LogStage.SCRAPING,
                infoleg_id=norm_id
            )

            # Get norm from data source
            norm = self.norm_provider.get_norm_by_id(norm_id)
            if not norm:
                logger.log_processing_failed(
                    infoleg_id=norm_id,
                    error="Norm not found in InfoLeg API"
                )
                return False, "norm_not_found"

            # Create scraper metadata
            scraper_metadata = ScraperMetadata(
                api_url=f"{self.norm_provider.settings.infoleg_api.base_url}{self.norm_provider.settings.infoleg_api.endpoints.norm_details}?id={norm_id}",
                scraper_version="2.0",
                has_full_text=bool(norm.texto_norma),
                scraping_timestamp=datetime.now().isoformat(),
                from_cache=False
            )

            # Create scraping data
            scraping_data = ScrapingData(
                infoleg_response=norm,
                scraper_metadata=scraper_metadata
            )

            # Create processed data container (only scraping part populated)
            processed_data = ProcessedData(
                scraping_data=scraping_data,
                processing_data=None  # Will be populated by processor
            )

            processed_data_dict = processed_data.to_dict()

            # Cache the result
            logger.info(
                "Caching scraped norm",
                stage=LogStage.CACHE_WRITE,
                infoleg_id=norm_id
            )
            self.cache.put(cache_key, processed_data_dict)

            # Send to queue
            success = self.queue.send_message('purifying', processed_data_dict)
            if success:
                duration_ms = (time.time() - start_time) * 1000
                logger.log_message_sent(
                    queue_name='purifying',
                    infoleg_id=norm_id,
                    from_cache=False
                )
                logger.log_processing_complete(
                    infoleg_id=norm_id,
                    duration_ms=duration_ms,
                    source="scraped",
                    tipo_norma=norm.tipo_norma,
                    has_original_text=bool(norm.texto_norma),
                    has_updated_text=bool(norm.texto_norma_actualizado)
                )
                return True, "scraped"
            else:
                logger.error(
                    "Failed to send scraped norm to queue",
                    stage=LogStage.QUEUE_ERROR,
                    infoleg_id=norm_id
                )
                return False, "queue_failed"

        except Exception as e:
            logger.log_processing_failed(
                infoleg_id=norm_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False, f"error: {str(e)}"

    def is_cached(self, norm_id: int) -> bool:
        """Check if a norm is cached"""
        cache_key = self._get_norm_cache_key(norm_id)
        return self.cache.exists(cache_key)

    def replay_norm(self, norm_id: int, force: bool = False) -> Tuple[bool, str]:
        """Replay a cached norm to the purifying queue"""
        start_time = time.time()

        logger.log_processing_start(infoleg_id=norm_id)

        # Get from cache
        cache_key = self._get_norm_cache_key(norm_id)
        cached_data = self.cache.get(cache_key)

        if not cached_data:
            logger.log_processing_failed(
                infoleg_id=norm_id,
                error="Norm not found in cache"
            )
            return False, "cache_miss"

        logger.log_cache_hit(infoleg_id=norm_id)

        # Update timestamp in metadata
        if 'scraping_data' in cached_data and 'scraper_metadata' in cached_data['scraping_data']:
            cached_data['scraping_data']['scraper_metadata']['from_cache'] = True
            cached_data['scraping_data']['scraper_metadata']['scraping_timestamp'] = datetime.now().isoformat()

        # Send to queue
        success = self.queue.send_message('purifying', cached_data)
        if success:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_message_sent(
                queue_name='purifying',
                infoleg_id=norm_id,
                from_cache=True
            )
            logger.log_processing_complete(
                infoleg_id=norm_id,
                duration_ms=duration_ms,
                source="cache"
            )
            return True, "cache"
        else:
            logger.error(
                "Failed to send cached norm to queue",
                stage=LogStage.QUEUE_ERROR,
                infoleg_id=norm_id
            )
            return False, "queue_send_failed"