from fastapi import APIRouter, Depends, HTTPException
from typing import Union
import logging

from ..models.requests import ScrapeRequest, ProcessRequest, ReplayRequest
from ..models.responses import HealthResponse, ScrapeResponse, ProcessResponse, ReplayResponse, ErrorResponse
from ..interfaces.scraper_interface import ScraperInterface
from ..dependencies import get_scraper_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint"""
    return HealthResponse()


@router.post("/scrape", response_model=Union[ScrapeResponse, ErrorResponse])
def scrape_norm(
    request: ScrapeRequest,
    scraper_service: ScraperInterface = Depends(get_scraper_service)
):
    """Endpoint to scrape a specific norm by ID with caching support"""
    try:
        logger.info(f"Received scrape request for norm ID: {request.infoleg_id} (force={request.force})")

        success, source = scraper_service.scrape_specific_norm(request.infoleg_id, force=request.force)

        if success:
            is_cache_hit = source == 'cache'
            status = 'cached' if is_cache_hit else 'success'
            message = f'Norm {request.infoleg_id} served from cache' if is_cache_hit else f'Successfully scraped norm {request.infoleg_id}'

            return ScrapeResponse(
                status=status,
                message=message,
                infoleg_id=request.infoleg_id,
                source=source,
                cache_hit=is_cache_hit,
                forced=request.force
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to scrape norm {request.infoleg_id}: {source}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/process", response_model=Union[ProcessResponse, ErrorResponse])
def process_norm(
    request: ProcessRequest,
    scraper_service: ScraperInterface = Depends(get_scraper_service)
):
    """Endpoint to scrape and send a specific norm to processing queue"""
    try:
        logger.info(f"Received process request for norm ID: {request.infoleg_id} (force={request.force})")

        success, source = scraper_service.scrape_specific_norm(request.infoleg_id, force=request.force)

        if success:
            is_cache_hit = source == 'cache'
            status = 'cached' if is_cache_hit else 'success'
            message = f'Norm {request.infoleg_id} processed from cache' if is_cache_hit else f'Successfully processed norm {request.infoleg_id}'

            return ProcessResponse(
                status=status,
                message=message,
                infoleg_id=request.infoleg_id,
                source=source,
                cache_hit=is_cache_hit,
                forced=request.force
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process norm {request.infoleg_id}: {source}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/replay", response_model=Union[ReplayResponse, ErrorResponse])
def replay_norm(
    request: ReplayRequest,
    scraper_service: ScraperInterface = Depends(get_scraper_service)
):
    """Endpoint to replay a cached norm to the purifying queue"""
    try:
        logger.info(f"Received replay request for norm ID: {request.infoleg_id} (force={request.force})")

        success, source = scraper_service.replay_norm(request.infoleg_id, force=request.force)

        if success:
            return ReplayResponse(
                status='success',
                message=f'Successfully replayed norm {request.infoleg_id} to purifying queue',
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