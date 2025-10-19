"""Dependency injection configuration for FastAPI"""

import os
from functools import lru_cache

from interfaces.norm_embedder_service_interface import NormEmbedderServiceInterface
from interfaces.embedder_service_interface import EmbedderServiceInterface
from services.norm_embedder_service import GeminiNormEmbedderService
from services.embedder_service import EmbedderService
from config.settings import get_settings


@lru_cache()
def get_norm_embedder_service() -> NormEmbedderServiceInterface:
    """Provide embedding model instance with caching"""
    config = get_settings()
    embedding_config = config.embedding

    if not embedding_config.api_key:
        raise ValueError("Gemini API key not configured")

    return GeminiNormEmbedderService(
        api_key=embedding_config.api_key,
        model_name=embedding_config.embedding_model_name,
        output_dimensionality=embedding_config.output_dimensionality
    )


def get_embedder_service() -> EmbedderServiceInterface:
    """Provide embedding service with injected dependencies"""
    norm_embedder_service = get_norm_embedder_service()
    return EmbedderService(norm_embedder_service)