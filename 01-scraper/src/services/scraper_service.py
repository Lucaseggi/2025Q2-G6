import sys
import os
import logging
from datetime import datetime
from typing import Tuple

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import ProcessedData, ScrapingData, ScraperMetadata
from rabbitmq_client import RabbitMQClient

from ..interfaces.scraper_interface import ScraperInterface
from ..interfaces.cache_interface import CacheInterface
from ..interfaces.queue_interface import QueueInterface
from ..interfaces.norm_provider_interface import NormProviderInterface

logger = logging.getLogger(__name__)


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
        logger.info(f"Scraping specific norm with ID: {norm_id} (force={force})")

        cache_key = self._get_norm_cache_key(norm_id)

        # Check cache first (unless force is True)
        if not force:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f"Using cached data for norm {norm_id}")
                # Mark as from cache and update timestamp
                if 'scraping_data' in cached_data and 'scraper_metadata' in cached_data['scraping_data']:
                    cached_data['scraping_data']['scraper_metadata']['from_cache'] = True
                    cached_data['scraping_data']['scraper_metadata']['scraping_timestamp'] = datetime.now().isoformat()

                # Return the cached processed_data
                success = self.queue.send_message('processing', cached_data)
                if success:
                    logger.info(f"Successfully sent cached norm {norm_id} to processing queue")
                    return True, "cache"
                else:
                    logger.error(f"Failed to send cached norm {norm_id}")
                    return False, "cache_send_failed"

        # If not in cache or force=True, scrape from data source
        try:
            # Get norm from data source
            norm = self.norm_provider.get_norm_by_id(norm_id)
            if not norm:
                logger.error(f"Could not retrieve norm {norm_id} from data source")
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
            self.cache.put(cache_key, processed_data_dict)

            # Send to queue
            success = self.queue.send_message('processing', processed_data_dict)
            if success:
                logger.info(f"Successfully sent norm {norm_id} ({norm.tipo_norma} - {norm.titulo_sumario[:50]}...)")
                logger.info(f"Norm details: Sancion date: {norm.sancion}, Has original text: {bool(norm.texto_norma)}, Has updated text: {bool(norm.texto_norma_actualizado)}")
                return True, "scraped"
            else:
                logger.error(f"Failed to send norm {norm_id}")
                return False, "queue_failed"

        except Exception as e:
            logger.error(f"Error scraping norm {norm_id}: {e}")
            return False, f"error: {str(e)}"

    def is_cached(self, norm_id: int) -> bool:
        """Check if a norm is cached"""
        cache_key = self._get_norm_cache_key(norm_id)
        return self.cache.exists(cache_key)