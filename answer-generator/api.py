"""Main entry point for the answer generator service"""

import logging
import uvicorn
from fastapi import FastAPI

from src.api.endpoints import router
from src.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Answer Generator API",
    description="Microservice for generating answers using RAG pipeline",
    version="1.0.0",
)

# Include API routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    settings = get_settings()
    logger.info(f"Answer Generator Service starting on {settings.service_host}:{settings.service_port}")
    logger.info(f"Embedder API: {settings.embedder_api_host}")
    logger.info(f"Vectorial API: {settings.vectorial_api_host}")
    logger.info(f"Relational API: {settings.relational_api_host}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Answer Generator Service shutting down")


if __name__ == "__main__":
    settings = get_settings()

    logger.info(f"Starting Answer Generator Service on {settings.service_host}:{settings.service_port}")

    uvicorn.run(
        "api:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level="info"
    )
