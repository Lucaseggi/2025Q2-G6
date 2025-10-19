import sys
import os
import logging
import requests
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from math import ceil

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import ProcessedData, ScrapingData, ScraperMetadata

from ..interfaces.scraper_interface import ScraperInterface
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class DailyScraperService:
    """Service for daily scraping of new norms from InfoLeg"""

    def __init__(self, settings: Settings, scraper_service: ScraperInterface):
        """Initialize daily scraper service"""
        self.settings = settings
        self.scraper_service = scraper_service
        
        # Initialize HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.infoleg_api.user_agent,
            'Accept': 'application/json'
        })
        self.session.verify = settings.infoleg_api.verify_ssl

        if not settings.infoleg_api.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make rate-limited request with retries"""
        for attempt in range(self.settings.infoleg_api.max_retries):
            try:
                time.sleep(self.settings.infoleg_api.rate_limit_delay)
                logger.debug(f"Making request to: {url} with params: {params}")

                response = self.session.get(
                    url, params=params, timeout=self.settings.infoleg_api.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.settings.infoleg_api.max_retries}): {e}")
                if attempt == self.settings.infoleg_api.max_retries - 1:
                    return None
                time.sleep(2**attempt)  # Exponential backoff

        return None

    def _get_norms_for_date(self, target_date: date) -> List[int]:
        """Get all norm IDs published on a specific date"""
        logger.info(f"Fetching norms published on {target_date}")
        
        date_str = target_date.strftime('%Y-%m-%d')
        norm_ids = []
        
        # Build URL for norms by date range (same day for both from and to)
        url = f"{self.settings.infoleg_api.base_url}{self.settings.infoleg_api.endpoints.norms_by_year}"
        
        # Start with first page to get total count
        params = {
            'publicacion_desde': date_str,
            'publicacion_hasta': date_str,
            'offset': 1,
            'limit': 25  # API default limit
        }
        
        first_response = self._make_request(url, params)
        if not first_response:
            logger.error(f"Failed to fetch first page for date {target_date}")
            return norm_ids
        
        # Extract metadata to understand pagination
        metadata = first_response.get('metadata', {})
        resultset = metadata.get('resultset', {})
        total_count = resultset.get('count', 0)
        limit = resultset.get('limit', 25)
        
        logger.info(f"Found {total_count} norms published on {target_date}")
        
        if total_count == 0:
            return norm_ids
        
        # Calculate total pages needed
        total_pages = ceil(total_count / limit)
        logger.info(f"Will need to fetch {total_pages} pages with limit {limit}")
        
        # Process all pages
        for page in range(1, total_pages + 1):
            params['offset'] = page
            
            logger.debug(f"Fetching page {page}/{total_pages}")
            response = self._make_request(url, params)
            
            if not response:
                logger.error(f"Failed to fetch page {page}")
                continue
            
            # Extract norm IDs from results
            results = response.get('results', [])
            page_norm_ids = [result.get('id') for result in results if result.get('id')]
            norm_ids.extend(page_norm_ids)
            
            logger.debug(f"Page {page}: found {len(page_norm_ids)} norm IDs")
        
        logger.info(f"Total norm IDs collected for {target_date}: {len(norm_ids)}")
        return norm_ids

    def scrape_daily_norms(self, target_date: Optional[date] = None, force: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Scrape all norms published on a specific date
        
        Args:
            target_date: Date to scrape norms for (defaults to yesterday)
            force: Whether to force re-scraping even if already cached
            
        Returns:
            Tuple of (success, message, stats)
        """
        if target_date is None:
            # Default to yesterday (assuming norms are published with 1-day delay)
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"Starting daily scrape for {target_date} (force={force})")
        
        try:
            # Get all norm IDs for the target date
            norm_ids = self._get_norms_for_date(target_date)
            
            if not norm_ids:
                message = f"No norms found for {target_date}"
                logger.info(message)
                return True, message, {
                    'target_date': target_date.isoformat(),
                    'total_norms': 0,
                    'scraped': 0,
                    'cached': 0,
                    'failed': 0
                }
            
            # Track statistics
            stats = {
                'target_date': target_date.isoformat(),
                'total_norms': len(norm_ids),
                'scraped': 0,
                'cached': 0,
                'failed': 0,
                'failed_ids': []
            }
            
            logger.info(f"Processing {len(norm_ids)} norms...")
            
            # Process each norm ID
            for i, norm_id in enumerate(norm_ids, 1):
                logger.info(f"Processing norm {i}/{len(norm_ids)}: {norm_id}")
                
                try:
                    success, source = self.scraper_service.scrape_specific_norm(norm_id, force=force)
                    
                    if success:
                        if source == 'cache':
                            stats['cached'] += 1
                            logger.debug(f"Norm {norm_id} served from cache")
                        else:
                            stats['scraped'] += 1
                            logger.debug(f"Norm {norm_id} scraped successfully")
                    else:
                        stats['failed'] += 1
                        stats['failed_ids'].append(norm_id)
                        logger.error(f"Failed to scrape norm {norm_id}: {source}")
                        
                except Exception as e:
                    stats['failed'] += 1
                    stats['failed_ids'].append(norm_id)
                    logger.error(f"Exception while processing norm {norm_id}: {e}")
                
                # Add small delay between requests to be respectful
                if i < len(norm_ids):  # Don't sleep after the last one
                    time.sleep(0.1)
            
            # Generate summary message
            message = (
                f"Daily scrape completed for {target_date}: "
                f"{stats['scraped']} scraped, {stats['cached']} from cache, "
                f"{stats['failed']} failed"
            )
            
            if stats['failed'] > 0:
                logger.warning(f"Failed to process {stats['failed']} norms: {stats['failed_ids']}")
            
            logger.info(message)
            return True, message, stats
            
        except Exception as e:
            error_msg = f"Daily scrape failed for {target_date}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {
                'target_date': target_date.isoformat() if target_date else None,
                'error': str(e)
            }

    def scrape_yesterday(self, force: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
        """Convenience method to scrape yesterday's norms"""
        yesterday = date.today() - timedelta(days=1)
        return self.scrape_daily_norms(yesterday, force)

    def scrape_date_range(self, start_date: date, end_date: date, force: bool = False) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Scrape norms for a range of dates
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            force: Whether to force re-scraping
            
        Returns:
            Tuple of (success, message, list of daily stats)
        """
        logger.info(f"Starting date range scrape from {start_date} to {end_date}")
        
        if start_date > end_date:
            return False, "Start date must be before or equal to end date", []
        
        all_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            success, message, stats = self.scrape_daily_norms(current_date, force)
            all_stats.append(stats)
            
            if not success:
                logger.error(f"Failed to scrape {current_date}: {message}")
            
            current_date += timedelta(days=1)
            
            # Add delay between days to be respectful
            if current_date <= end_date:
                time.sleep(2.0)
        
        # Calculate totals
        total_norms = sum(stats.get('total_norms', 0) for stats in all_stats)
        total_scraped = sum(stats.get('scraped', 0) for stats in all_stats)
        total_cached = sum(stats.get('cached', 0) for stats in all_stats)
        total_failed = sum(stats.get('failed', 0) for stats in all_stats)
        
        summary_message = (
            f"Date range scrape completed ({start_date} to {end_date}): "
            f"{total_norms} total norms, {total_scraped} scraped, "
            f"{total_cached} from cache, {total_failed} failed"
        )
        
        logger.info(summary_message)
        return True, summary_message, all_stats