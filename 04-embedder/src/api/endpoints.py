"""API endpoints for embedding service"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

# Add src to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Add shared models to path BEFORE any interface imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from api_models.requests import EmbedRequest
from api_models.responses import EmbedResponse, HealthResponse
from interfaces.embedder_service_interface import EmbedderServiceInterface
from dependencies import get_embedder_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(service: EmbedderServiceInterface = Depends(get_embedder_service)):
    """Health check endpoint"""
    model_status = "available" if service.is_available() else "unavailable"

    return HealthResponse(
        status="healthy",
        service="embedding-ms",
        embedding_model_status=model_status,
        timestamp=datetime.now()
    )


@router.post("/embed", response_model=EmbedResponse)
async def embed_text(
    request: EmbedRequest,
    service: EmbedderServiceInterface = Depends(get_embedder_service)
):
    """Generate embedding for a single text"""
    try:
        logger.info(f"Generating embedding for text ({len(request.text)} chars)")

        embedding = service.embed_text(request.text)

        if embedding is None:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")

        return EmbedResponse(
            embedding=embedding,
            model="embedding-service",
            dimensions=len(embedding),
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))