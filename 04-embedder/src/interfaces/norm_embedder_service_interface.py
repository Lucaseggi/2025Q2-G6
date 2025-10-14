"""Interface for embedding model providers"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class NormEmbedderServiceInterface(ABC):
    """Interface for norm embedder services"""

    @abstractmethod
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for the given text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name/identifier of the embedding model.

        Returns:
            Model name
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the embedding model is properly configured and available.

        Returns:
            True if available, False otherwise
        """
        pass