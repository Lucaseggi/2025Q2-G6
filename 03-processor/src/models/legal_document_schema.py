"""Pydantic models for structured legal document output from Gemini API"""

from typing import List
from pydantic import BaseModel, Field


class Article(BaseModel):
    """Represents an article in a legal document (recursive structure)"""
    ordinal: str = Field(description="Number, letter or identifier of the article (e.g., '1', 'a', 'bis'). Empty string if none.")
    body: str = Field(description="Full text of the article without the word 'Article' or number")
    articles: List['Article'] = Field(default_factory=list, description="Sub-articles (recursive)")

    class Config:
        # Allow forward references for recursive structures
        arbitrary_types_allowed = True


class Division(BaseModel):
    """Represents a division in a legal document (recursive structure)"""
    name: str = Field(description="Name of the division (e.g., 'Título', 'Capítulo', 'Preambulo', 'Consideraciones')")
    ordinal: str = Field(description="Number, letter or identifier if present (e.g., '1', 'I', 'III'). Empty string if none.")
    title: str = Field(description="Full heading of the division")
    body: str = Field(description="Main text of the division")
    articles: List[Article] = Field(default_factory=list, description="Articles within this division")
    divisions: List['Division'] = Field(default_factory=list, description="Sub-divisions (recursive)")

    class Config:
        # Allow forward references for recursive structures
        arbitrary_types_allowed = True


# Update forward references to resolve recursive types
Article.model_rebuild()
Division.model_rebuild()


class LegalDocument(BaseModel):
    """Root structure for a legal document"""
    divisions: List[Division] = Field(description="Top-level divisions of the document")
