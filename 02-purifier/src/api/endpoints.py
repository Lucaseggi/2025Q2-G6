from fastapi import APIRouter, Depends, HTTPException
from typing import Union
import logging

from ..models.requests import ReplayRequest
from ..models.responses import HealthResponse, ReplayResponse, ErrorResponse
from ..interfaces.purifier_interface import PurifierInterface
from ..dependencies import get_purifier_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint"""
    return HealthResponse()


@router.post("/replay", response_model=Union[ReplayResponse, ErrorResponse])
def replay_norm(
    request: ReplayRequest,
    purifier_service: PurifierInterface = Depends(get_purifier_service)
):
    """Endpoint to replay a specific norm from cache to purification queue"""
    try:
        logger.info(f"Received replay request for norm ID: {request.infoleg_id} (force={request.force})")

        success, source = purifier_service.replay_norm(request.infoleg_id, force=request.force)

        if success:
            return ReplayResponse(
                status='success',
                message=f'Successfully replayed norm {request.infoleg_id} to processing queue',
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
