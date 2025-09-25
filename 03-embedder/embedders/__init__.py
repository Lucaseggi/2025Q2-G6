"""Embedder module initialization"""

from .base import BaseEmbedder, EmbedderType
from .gemini_embedder import GeminiEmbedder

__all__ = ['BaseEmbedder', 'EmbedderType', 'GeminiEmbedder', 'create_embedder']


def create_embedder(embedder_type: str, config: dict = None) -> BaseEmbedder:
    """
    Factory function to create embedder instances.

    Args:
        embedder_type (str): Type of embedder ('gemini', 'local', etc.)
        config (dict): Configuration for the embedder

    Returns:
        BaseEmbedder: Configured embedder instance

    Raises:
        ValueError: If embedder_type is not supported
    """
    embedder_type = embedder_type.lower()

    if embedder_type == 'gemini':
        return GeminiEmbedder(config)
    else:
        raise ValueError(f"Unsupported embedder type: {embedder_type}")