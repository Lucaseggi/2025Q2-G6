"""Dependency injection configuration for FastAPI"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.config.settings import get_settings
from src.interfaces.parsing_service_interface import ParsingServiceInterface
from src.interfaces.queue_interface import QueueInterface
from src.services.text_processing_service import TextProcessingService
from src.services.llm_service import LLMService
from src.services.verification_service import VerificationService
from src.services.storage_service import StorageService
from src.services.queue_service import QueueService
from src.services.parsing_service import ParsingService
from src.services.cache_replay_service import CacheReplayService


def get_processor_settings():
    """Get settings instance"""
    return get_settings()


def get_text_processor() -> TextProcessingService:
    """Provide text processing service instance"""
    return TextProcessingService()


def get_llm_service() -> LLMService:
    """Provide LLM service instance"""
    settings = get_processor_settings()
    return LLMService(settings)


def get_verification_service() -> VerificationService:
    """Provide verification service instance"""
    settings = get_processor_settings()
    return VerificationService(
        similarity_threshold=getattr(settings.gemini, 'diff_threshold', 0.15)
    )


def get_storage_service() -> StorageService:
    """Provide storage service instance"""
    settings = get_processor_settings()
    return StorageService(settings)


def get_queue_service() -> QueueInterface:
    """Provide queue service instance"""
    settings = get_processor_settings()
    return QueueService(settings)


def get_parsing_service() -> ParsingServiceInterface:
    """Provide parsing service with injected dependencies"""
    text_processor = get_text_processor()
    llm = get_llm_service()
    verification = get_verification_service()
    storage = get_storage_service()
    return ParsingService(text_processor, llm, verification, storage)


def get_cache_replay_service() -> CacheReplayService:
    """Provide cache replay service instance"""
    storage = get_storage_service()
    settings = get_processor_settings()
    return CacheReplayService(storage, settings)
