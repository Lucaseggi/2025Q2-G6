"""Request models for the answer generator API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict


class QuestionRequest(BaseModel):
    """Request model for question endpoint"""
    question: str = Field(..., min_length=1, description="User's question")
    filters: Optional[Dict[str, str]] = Field(default=None, description="Optional metadata filters for vector search")
    limit: Optional[int] = Field(default=5, ge=1, le=20, description="Maximum number of results to retrieve")
