"""Dependency injection configuration for FastAPI"""

from functools import lru_cache
from .config.settings import get_settings, Settings
from .interfaces.cache_interface import CacheInterface
from .interfaces.queue_interface import QueueInterface
from .interfaces.norm_provider_interface import NormProviderInterface
from .interfaces.scraper_interface import ScraperInterface

from .services.cache_service import CacheService
from .services.queue_service import QueueService
from .services.infoleg_norm_provider import InfolegNormProvider
from .services.scraper_service import ScraperService
from .services.daily_scraper_service import DailyScraperService
from .services.scheduler_service import SchedulerService


@lru_cache()
def get_settings_cached() -> Settings:
    """Get cached settings instance"""
    return get_settings()


def get_cache_service() -> CacheInterface:
    """Provide cache service instance"""
    settings = get_settings_cached()
    return CacheService(settings)


def get_queue_service() -> QueueInterface:
    """Provide queue service instance"""
    settings = get_settings_cached()
    return QueueService(settings)


def get_norm_provider_service() -> NormProviderInterface:
    """Provide InfoLeg norm provider instance"""
    settings = get_settings_cached()
    return InfolegNormProvider(settings)


def get_scraper_service() -> ScraperInterface:
    """Provide scraper service with injected dependencies"""
    cache = get_cache_service()
    queue = get_queue_service()
    norm_provider = get_norm_provider_service()
    return ScraperService(cache, queue, norm_provider)


def get_daily_scraper_service() -> DailyScraperService:
    """Provide daily scraper service with injected dependencies"""
    settings = get_settings_cached()
    scraper_service = get_scraper_service()
    return DailyScraperService(settings, scraper_service)


def get_scheduler_service() -> SchedulerService:
    """Provide scheduler service with injected dependencies"""
    daily_scraper_service = get_daily_scraper_service()
    return SchedulerService(daily_scraper_service)