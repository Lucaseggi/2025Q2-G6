"""API endpoints for answer generator service"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from src.api_models.requests import QuestionRequest
from src.api_models.responses import QuestionResponse, HealthResponse
from src.services.rag_service import RAGService
from src.dependencies import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="answer-generator",
        timestamp=datetime.now(),
        dependencies={
            "embedder": "not_checked",
            "vectorial_guard": "not_checked",
            "relational_guard": "not_checked"
        }
    )


@router.post("/question", response_model=QuestionResponse)
async def answer_question(
    request: QuestionRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Process a question and retrieve relevant legal context.

    This endpoint orchestrates the RAG pipeline:
    1. Generates embedding for the question
    2. Searches for similar vectors
    3. Fetches relevant legal entities
    4. Returns structured context
    """
    try:
        logger.info(f"Processing question: {request.question[:100]}...")

        # Get context from RAG service
        result = rag_service.get_context_for_question(
            question=request.question,
            filters=request.filters,
            limit=request.limit or 5
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Failed to retrieve context")
            )

        return QuestionResponse(
            success=True,
            question=request.question,
            context=result["context"],
            answer=result.get("answer", ""),
            message=result["message"],
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
