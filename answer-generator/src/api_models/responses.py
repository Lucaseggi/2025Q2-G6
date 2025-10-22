"""Response models for the answer generator API"""

from pydantic import BaseModel, Field
from typing import List, Any, Optional
from datetime import datetime


class QuestionResponse(BaseModel):
    """Response model for question endpoint"""
    success: bool = Field(..., description="Whether the request was successful")
    question: str = Field(..., description="The original question")
    context: dict = Field(..., description="Retrieved context with normas_data and norma_ids")
    answer: str = Field(default="", description="Generated answer from LLM based on context")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")
    dependencies: Optional[dict] = Field(default=None, description="Status of dependent services")
