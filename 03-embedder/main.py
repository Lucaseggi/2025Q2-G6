"""Main entry point for the embedding service (API + Queue Processing)"""

import os
import logging
import threading
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.endpoints import router
from src.dependencies import get_embedder_service
from src.queue_processor import QueueProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("Embedding Service API started")

    # Start queue processor in background thread
    queue_thread = threading.Thread(
        target=start_queue_processor,
        name="QueueProcessor",
        daemon=True
    )
    queue_thread.start()
    logger.info("Queue processor thread started")

    yield

    # Shutdown (if needed)
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


def start_queue_processor():
    """Start the queue processor in a background thread"""
    try:
        # Get embedder service with dependency injection
        embedder_service = get_embedder_service()

        if not embedder_service.is_available():
            logger.error("Embedder service not available for queue processing")
            return

        logger.info("Starting queue processor thread...")

        # Start queue processor
        processor = QueueProcessor(embedder_service)
        processor.process_documents_from_queue()

    except Exception as e:
        logger.error(f"Error in queue processor: {e}")



if __name__ == "__main__":
    port = int(os.getenv('EMBEDDING_PORT', 8005))
    host = os.getenv('EMBEDDING_HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', '0') == '1'

    logger.info(f"Starting Embedding Service on {host}:{port}")
    logger.info("Service will handle both API requests and queue processing")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )