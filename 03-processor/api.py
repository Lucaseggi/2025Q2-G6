"""FastAPI application for processor service"""

import sys
sys.path.insert(0, '/app/shared')

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.config.settings import get_settings
from src.api.endpoints import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    logger.info("Processor API started")
    logger.info(f"Running on port 8005")

    yield

    logger.info("Processor API shutting down")

app = FastAPI(
    title="Processor API",
    description="Microservice for LLM-based document structuring",
    version=settings.service.version,
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8005,
        reload=settings.service.debug,
        log_level="info"
    )
