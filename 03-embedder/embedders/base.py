"""Abstract base class for embedding providers"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum


class EmbedderType(Enum):
    """Types of embedding providers"""
    LOCAL_MODEL = "local_model"
    API_SERVICE = "api_service"
    HYBRID = "hybrid"


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize embedder with configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config or {}

    @abstractmethod
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for the given text.

        Args:
            text (str): Text to embed

        Returns:
            Optional[List[float]]: Embedding vector or None if failed
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this embedder.

        Returns:
            int: Embedding dimension
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name/identifier of the embedding model.

        Returns:
            str: Model name
        """
        pass

    @abstractmethod
    def get_embedder_type(self) -> EmbedderType:
        """
        Get the type of embedder (local, API, hybrid).

        Returns:
            EmbedderType: Type of embedder
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the embedder is properly configured and available.

        Returns:
            bool: True if available, False otherwise
        """
        pass

    @abstractmethod
    def load_model(self) -> bool:
        """
        Load/initialize the model. For local models, this loads the model into memory.
        For API services, this validates the connection.

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def unload_model(self) -> bool:
        """
        Unload/cleanup the model. For local models, this frees memory.
        For API services, this cleans up connections.

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the model.

        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "model_name": self.get_model_name(),
            "embedder_type": self.get_embedder_type().value,
            "embedding_dimension": self.get_embedding_dimension(),
            "is_available": self.is_available(),
            "config": self.config
        }

    def batch_generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts. Default implementation processes one by one.
        Subclasses can override for more efficient batch processing.

        Args:
            texts (List[str]): List of texts to embed

        Returns:
            List[Optional[List[float]]]: List of embedding vectors
        """
        return [self.generate_embedding(text) for text in texts]