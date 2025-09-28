"""Gemini norm embedder service implementation"""

import os
import logging
from typing import Optional, List, Dict, Any

from google import genai
from google.genai import types

# Add src to path for interfaces
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from interfaces.norm_embedder_service_interface import NormEmbedderServiceInterface

logger = logging.getLogger(__name__)


class GeminiNormEmbedderService(NormEmbedderServiceInterface):
    """Gemini API norm embedder service implementation"""

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001", output_dimensionality: int = 768):
        """
        Initialize Gemini embedding model.

        Args:
            api_key: Gemini API key
            model_name: Name of the Gemini embedding model
            output_dimensionality: Dimension of output embeddings
        """
        self.api_key = api_key
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> bool:
        """Initialize Gemini client"""
        if not self.api_key:
            logger.error("No Gemini API key provided")
            return False

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            return False

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Gemini API"""
        if not self.client:
            if not self._initialize_client():
                return None

        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            result = self.client.models.embed_content(
                model=self.model_name,
                contents=text.strip(),
                config=types.EmbedContentConfig(output_dimensionality=self.output_dimensionality),
            )

            # Extract the embedding values as a list
            [embedding_obj] = result.embeddings
            embedding = list(embedding_obj.values)

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self.output_dimensionality

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name

    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        if not self.api_key:
            return False

        if not self.client:
            return self._initialize_client()

        return True