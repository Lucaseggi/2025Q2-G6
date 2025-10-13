"""Dependency injection configuration for FastAPI"""

from functools import lru_cache
from .config.settings import get_settings, Settings
from .interfaces.cache_interface import CacheInterface
from .interfaces.queue_interface import QueueInterface
from .interfaces.purifier_interface import PurifierInterface

from .services.cache_service import CacheService
from .services.queue_service import QueueService
from .services.text_processing_service import TextProcessingService
from .services.llm_service import LLMService
from .services.purifier_service import PurifierService


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


def get_text_processor() -> TextProcessingService:
    """Provide text processing service instance"""
    return TextProcessingService()


def get_llm_service() -> LLMService:
    """Provide LLM service instance"""
    settings = get_settings_cached()
    return LLMService(settings)


def get_purifier_service() -> PurifierInterface:
    """Provide purifier service with injected dependencies"""
    cache = get_cache_service()
    queue = get_queue_service()
    text_processor = get_text_processor()
    llm = get_llm_service()
    return PurifierService(cache, queue, text_processor, llm)
