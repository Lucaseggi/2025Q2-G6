"""Gemini API embedding provider"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime

from google import genai
from google.genai import types

from .base import BaseEmbedder, EmbedderType


class GeminiEmbedder(BaseEmbedder):
    """Gemini API embedding provider"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.client = None
        self.model_name = self.config.get('model_name', 'gemini-embedding-001')
        self.output_dimensionality = self.config.get('output_dimensionality', 768)
        self.api_key = self.config.get('api_key') or os.getenv('GEMINI_API_KEY')

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Gemini API"""
        if not self.client:
            if not self.load_model():
                return None

        try:
            result = self.client.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=self.output_dimensionality),
            )

            # Extract the embedding values as a list
            [embedding_obj] = result.embeddings
            embedding = list(embedding_obj.values)

            print(
                f"[{datetime.now()}] GeminiEmbedder: Generated {len(embedding)}-dimensional embedding"
            )
            return embedding

        except Exception as e:
            print(f"[{datetime.now()}] GeminiEmbedder: Error generating embedding: {e}")
            return None

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self.output_dimensionality

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name

    def get_embedder_type(self) -> EmbedderType:
        """Get embedder type"""
        return EmbedderType.API_SERVICE

    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        if not self.api_key:
            print(f"[{datetime.now()}] GeminiEmbedder: No API key available")
            return False

        if not self.client:
            return self.load_model()

        return True

    def load_model(self) -> bool:
        """Initialize Gemini client"""
        if not self.api_key:
            print(f"[{datetime.now()}] GeminiEmbedder: GEMINI_API_KEY not set")
            return False

        try:
            self.client = genai.Client(api_key=self.api_key)
            print(f"[{datetime.now()}] GeminiEmbedder: Client initialized successfully")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] GeminiEmbedder: Error initializing client: {e}")
            return False

    def unload_model(self) -> bool:
        """Cleanup Gemini client"""
        try:
            self.client = None
            print(f"[{datetime.now()}] GeminiEmbedder: Client unloaded")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] GeminiEmbedder: Error unloading client: {e}")
            return False

    def batch_generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        Gemini API doesn't have native batch support, so we process individually.
        """
        return [self.generate_embedding(text) for text in texts]