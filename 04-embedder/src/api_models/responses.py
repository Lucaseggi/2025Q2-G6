"""Response models for the embedding API"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class EmbedResponse(BaseModel):
    """Response model for single text embedding"""
    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used for embedding")
    dimensions: int = Field(..., description="Dimension of the embedding")
    timestamp: datetime = Field(..., description="Timestamp of embedding generation")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    embedding_model_status: str = Field(..., description="Embedding model status")
    timestamp: datetime = Field(..., description="Health check timestamp")