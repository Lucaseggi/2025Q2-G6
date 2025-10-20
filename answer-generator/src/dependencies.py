"""Dependency injection for services"""

from src.services.rag_service import RAGService
from src.config.settings import get_settings

# Singleton instances
_rag_service = None
_settings = None


def get_rag_service() -> RAGService:
    """Get or create RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_settings_dependency():
    """Get settings instance for FastAPI dependency"""
    return get_settings()
