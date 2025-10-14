"""Interface for embedding service"""

from abc import ABC, abstractmethod
from typing import Optional, List
import sys
import os

# Add shared models to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import ProcessedData


class EmbedderServiceInterface(ABC):
    """Interface for the main embedder service that coordinates document processing"""

    @abstractmethod
    def process_document(self, input_data: ProcessedData) -> Optional[ProcessedData]:
        """
        Process a document and add embeddings to its structured data.

        Args:
            input_data: ProcessedData object from the processor service

        Returns:
            ProcessedData with embeddings added, or None if failed
        """
        pass

    @abstractmethod
    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text prompt.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the embedding service is available.

        Returns:
            True if service is available, False otherwise
        """
        pass