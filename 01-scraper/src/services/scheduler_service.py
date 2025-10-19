import logging
from .daily_scraper_service import DailyScraperService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for manually triggering daily scraping tasks (AWS Lambda compatible)"""

    def __init__(self, daily_scraper_service: DailyScraperService):
        """Initialize scheduler service"""
        self.daily_scraper_service = daily_scraper_service
        logger.info("Scheduler service initialized for AWS Lambda (no internal scheduling)")

    def _run_daily_scraping_job(self, force: bool = False):
        """Execute the daily scraping job"""
        logger.info("Starting daily scraping job")
        
        try:
            success, message, stats = self.daily_scraper_service.scrape_yesterday(force=force)
            
            if success:
                logger.info(f"Daily scraping job completed: {message}")
                logger.info(f"Stats: {stats}")
            else:
                logger.error(f"Daily scraping job failed: {message}")
                
        except Exception as e:
            logger.error(f"Exception in daily scraping job: {e}")

    def run_manual_daily_scraping(self, force: bool = False):
        """Manually trigger daily scraping job (AWS Lambda entry point)"""
        logger.info("Running manual daily scraping (triggered by AWS)")
        self._run_daily_scraping_job(force=force)