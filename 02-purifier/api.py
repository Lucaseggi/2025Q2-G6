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
    logger.info("Purifier API started")
    logger.info(f"Running on port {settings.port}")

    yield

    logger.info("Purifier API shutting down")

app = FastAPI(
    title="Purifier API",
    description="Microservice for text purification with orthography fixes",
    version=settings.service.version,
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=settings.service.port,
        reload=settings.service.debug,
        log_level="info"
    )
