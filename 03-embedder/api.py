"""API-only entry point for the embedding service"""

import sys
sys.path.insert(0, '/app/shared')

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.endpoints import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    logger.info("Embedding Service API started (API-only mode)")
    logger.info("Running on port 8001")

    yield

    logger.info("Embedding Service API shutting down")


# Create FastAPI app
app = FastAPI(
    title="Embedding Service API",
    description="Microservice for generating text embeddings using various models",
    version="2.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('EMBEDDING_PORT', 8001))
    host = os.getenv('EMBEDDING_HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', '0') == '1'

    uvicorn.run(
        "embedder_api:app",  # Changed from "api:app"
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
