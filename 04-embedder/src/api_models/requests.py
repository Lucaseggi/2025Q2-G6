"""Request models for the embedding API"""

from pydantic import BaseModel, Field


class EmbedRequest(BaseModel):
    """Request model for single text embedding"""
    text: str = Field(..., min_length=1, description="Text to embed")