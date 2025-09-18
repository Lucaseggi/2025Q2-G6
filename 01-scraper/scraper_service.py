import os
import sys
import time
import logging
from datetime import datetime
from typing import Tuple, Dict, Any

sys.path.append('/app/00-shared')
from rabbitmq_client import RabbitMQClient
from models import ScrapedData, InfolegNorma
from api_client import ApiClient, ApiClientConfig
from s3_cache import S3Cache

logger = logging.getLogger(__name__)


class ScraperService:
    """Enhanced scraper service with S3 caching support"""

    def __init__(self):
        self.cache = S3Cache()
        self.queue_client = RabbitMQClient()
        self.api_client = ApiClient()

    def scrape_specific_norma(self, norma_id: int, force: bool = False, use_cache: bool = True) -> Tuple[bool, str]:
        """Scrape a specific norma by its infoleg_id with caching support"""
        logger.info(f"Scraping specific norma with ID: {norma_id} (force={force}, use_cache={use_cache})")

        cache = self.cache if use_cache else None

        # Check cache first (unless force is True)
        if cache and not force:
            cached_data = cache.get_cached_norma(norma_id)
            if cached_data:
                logger.info(f"Using cached data for norma {norma_id}")
                # Return the cached scraped_data
                success = self.queue_client.send_message('processing', cached_data['data'])
                if success:
                    logger.info(f"Successfully sent cached norma {norma_id} to processing queue")
                    return True, "cache"
                else:
                    logger.error(f"Failed to send cached norma {norma_id}")
                    return False, "cache_send_failed"

        # If not in cache or force=True, scrape from API
        try:
            # Get detailed information for this specific norm
            detailed_norm = self.api_client.get_norm_details(norma_id)
            if not detailed_norm:
                logger.error(f"Could not retrieve details for norm {norma_id}")
                return False, "api_failed"

            # Parse the response
            parsed_norm = self.api_client.parse_norm_response(detailed_norm)

            # Create InfolegNorma object
            norma = InfolegNorma(**parsed_norm)

            # Create ScrapedData
            scraped_data = ScrapedData(
                norma=norma,
                api_url=f"{self.api_client.config.base_url}{self.api_client.endpoints['norm_details']}?id={norma_id}",
                metadata={
                    "scraper_version": "2.0",
                    "scrape_mode": "specific_target_cached",
                    "api_source": "infoleg.gob.ar",
                    "has_full_text": bool(norma.texto_norma),
                    "has_updated_text": bool(norma.texto_norma_actualizado),
                    "from_cache": False,
                    "force_scraped": force,
                },
                timestamp=datetime.now().isoformat(),
            )

            scraped_data_dict = scraped_data.to_dict()

            # Cache the result
            if cache:
                cache.cache_norma(norma_id, scraped_data_dict)

            # Send to queue - use to_dict() which handles date serialization
            success = self.queue_client.send_message('processing', scraped_data_dict)
            if success:
                logger.info(
                    f"Successfully sent norma {norma_id} ({norma.tipo_norma} - {norma.titulo_sumario[:50]}...)"
                )
                logger.info(
                    f"Norma details: Sancion date: {norma.sancion}, Has original text: {bool(norma.texto_norma)}, Has updated text: {bool(norma.texto_norma_actualizado)}"
                )
                return True, "scraped"
            else:
                logger.error(f"Failed to send norma {norma_id}")
                return False, "queue_failed"

        except Exception as e:
            logger.error(f"Error scraping norma {norma_id}: {e}")
            return False, f"error: {str(e)}"

    def scrape_range(self, start_id: int, end_id: int, max_docs: int = 10, force: bool = False) -> Dict[str, Any]:
        """Scrape a range of normas"""
        logger.info(f"Scraping range {start_id}-{end_id}, max {max_docs} (force={force})")

        scraped_count = 0
        cached_count = 0
        failed_count = 0
        results = []

        for norma_id in range(start_id, min(end_id + 1, start_id + max_docs)):
            try:
                # Check if already cached (unless forcing)
                if not force and self.cache.is_cached(norma_id):
                    logger.info(f"Norma {norma_id} already cached, skipping")
                    cached_count += 1
                    results.append({
                        'norma_id': norma_id,
                        'status': 'cached',
                        'source': 'cache'
                    })
                    continue

                success, source = self.scrape_specific_norma(norma_id, force=force)
                if success:
                    scraped_count += 1
                    results.append({
                        'norma_id': norma_id,
                        'status': 'success',
                        'source': source
                    })
                else:
                    failed_count += 1
                    results.append({
                        'norma_id': norma_id,
                        'status': 'failed',
                        'reason': source
                    })

                # Small delay between requests
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error scraping norma {norma_id}: {e}")
                failed_count += 1
                results.append({
                    'norma_id': norma_id,
                    'status': 'failed',
                    'reason': str(e)
                })

        return {
            'scraped_count': scraped_count,
            'cached_count': cached_count,
            'failed_count': failed_count,
            'total_requested': min(max_docs, end_id - start_id + 1),
            'results': results
        }

    def process_range(self, start_id: int, end_id: int, max_docs: int = 10) -> Dict[str, Any]:
        """Process a range of normas (force scrape and send to processing)"""
        logger.info(f"Processing range {start_id}-{end_id}, max {max_docs} (force=True)")

        processed_count = 0
        failed_count = 0
        results = []

        for norma_id in range(start_id, min(end_id + 1, start_id + max_docs)):
            try:
                # Force scrape and process
                success, source = self.scrape_specific_norma(norma_id, force=True)
                if success:
                    processed_count += 1
                    results.append({
                        'norma_id': norma_id,
                        'status': 'success',
                        'source': source
                    })
                else:
                    failed_count += 1
                    results.append({
                        'norma_id': norma_id,
                        'status': 'failed',
                        'reason': source
                    })

                # Small delay between requests
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing norma {norma_id}: {e}")
                failed_count += 1
                results.append({
                    'norma_id': norma_id,
                    'status': 'failed',
                    'reason': str(e)
                })

        return {
            'processed_count': processed_count,
            'failed_count': failed_count,
            'total_requested': min(max_docs, end_id - start_id + 1),
            'results': results
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_cache_stats()

    def list_cached_normas(self, limit: int = 100) -> list:
        """List cached norma IDs"""
        return self.cache.list_cached_normas(limit=limit)

    def is_cached(self, norma_id: int) -> bool:
        """Check if norma is cached"""
        return self.cache.is_cached(norma_id)