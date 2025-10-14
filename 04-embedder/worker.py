"""Worker-only entry point for the embedding service"""

import sys
import os

# Add shared modules to path
sys.path.insert(0, '/app/shared')

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from dependencies import get_embedder_service
from queue_processor import QueueProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for embedder worker"""
    logger.info("Starting Embedder Worker (worker-only mode)...")

    try:
        # Get embedder service with dependency injection
        embedder_service = get_embedder_service()

        if not embedder_service.is_available():
            logger.error("Embedder service not available. Exiting.")
            return

        logger.info("Embedder service initialized successfully")

        # Start queue processor (blocks indefinitely)
        processor = QueueProcessor(embedder_service)
        processor.process_documents_from_queue()

    except KeyboardInterrupt:
        logger.info("Shutting down embedder worker...")
    except Exception as e:
        logger.error(f"Error in embedder worker: {e}")
        raise


if __name__ == "__main__":
    main()
