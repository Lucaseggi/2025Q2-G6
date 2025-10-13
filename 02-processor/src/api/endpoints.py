from fastapi import APIRouter, Depends, HTTPException
from typing import Union
import logging

from ..models.requests import ReplayRequest
from ..models.responses import HealthResponse, ReplayResponse, ErrorResponse
from ..interfaces.parsing_service_interface import ParsingServiceInterface
from ..services.cache_replay_service import CacheReplayService
from ..dependencies import get_parsing_service, get_cache_replay_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint"""
    return HealthResponse()


@router.post("/replay", response_model=Union[ReplayResponse, ErrorResponse])
def replay_norm(
    request: ReplayRequest,
    cache_replay_service: CacheReplayService = Depends(get_cache_replay_service)
):
    """Endpoint to replay a specific norm from cache to embedding queue"""
    try:
        logger.info(f"Received replay request for norm ID: {request.infoleg_id} (force={request.force})")

        success, source = cache_replay_service.replay_norm(request.infoleg_id, force=request.force)

        if success:
            return ReplayResponse(
                status='success',
                message=f'Successfully replayed norm {request.infoleg_id} to embedding queue',
                infoleg_id=request.infoleg_id,
                cache_hit=True
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to replay norm {request.infoleg_id}: {source}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in replay endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
