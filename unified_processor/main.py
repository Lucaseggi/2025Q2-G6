#!/usr/bin/env python3
"""
Unified Norm Processor
Combines purification and LLM structuring with intelligent model scaling
"""

import asyncio
import logging
import sys
from pathlib import Path

from src.config import Config
from src.database import DatabaseManager
from src.processor import UnifiedProcessor
from src.utils import setup_logging


async def main():
    """Main entry point"""
    logger = None
    db_manager = None
    
    try:
        # Load configuration
        config = Config.load('config.yaml')
        
        # Setup logging
        setup_logging(config.logging)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Unified Norm Processor")
        logger.info(f"Configuration loaded: {len(config.gemini.api_keys)} API keys, "
                   f"{len(config.gemini.models)} models available")
        
        # Initialize database manager
        db_manager = DatabaseManager(config)
        await db_manager.initialize()
        
        # Initialize processor
        processor = UnifiedProcessor(config, db_manager)
        
        # Start processing
        await processor.run()
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Received interrupt signal, shutting down gracefully...")
        else:
            print("Received interrupt signal, shutting down gracefully...")
    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error: {e}")
        return 1
    finally:
        if db_manager:
            await db_manager.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))