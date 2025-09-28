"""Main entry point for the processor service with clean architecture"""

import logging
import sys
import time
import os
from datetime import datetime
from typing import Optional

# Add shared modules to path
sys.path.append('/app/shared')
from rabbitmq_client import RabbitMQClient
from models import ProcessedData

# Add local src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from services.parsing_service import ParsingService
from services.text_processing_service import TextProcessingService
from services.llm_service import LLMService
from services.verification_service import VerificationService

from config import ProcessorSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main document processor with clean architecture"""

    def __init__(self):
        """Initialize document processor with dependency injection"""
        logger.info("Initializing Document Processor...")

        # Load configuration
        self.config = ProcessorSettings()

        # Initialize shared components
        self.queue_client = RabbitMQClient()

        # Initialize services with dependency injection
        self.text_processor = TextProcessingService()
        self.llm_service = LLMService(self.config)
        self.verification_service = VerificationService(
            similarity_threshold=getattr(self.config.gemini, 'diff_threshold', 0.15)
        )

        # Initialize main parsing service
        self.parsing_service = ParsingService(
            text_processor=self.text_processor,
            llm_service=self.llm_service,
            verification_service=self.verification_service
        )

        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'queue_failures': 0,
        }

        logger.info("Document Processor initialized successfully")

    def process_document(self, input_data: ProcessedData) -> Optional[ProcessedData]:
        """Process a single document through the parsing pipeline"""
        try:
            self.stats['total_processed'] += 1
            infoleg_id = input_data.scraping_data.infoleg_response.infoleg_id

            logger.info(f"Processing document {infoleg_id}")

            # Process through parsing service
            processed_data = self.parsing_service.process_document(input_data)

            if processed_data:
                self.stats['successful'] += 1

                # Processed data is ready for next stage

                logger.info(f"Successfully processed document {infoleg_id}")
                return processed_data
            else:
                self.stats['failed'] += 1
                logger.error(f"Failed to process document {infoleg_id}")
                return None

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Error processing document: {e}")
            return None

    def log_statistics(self):
        """Log current processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return

        success_rate = (self.stats['successful'] / total) * 100

        logger.info("=" * 80)
        logger.info("PROCESSING STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total processed:           {total}")
        logger.info(f"✓ Successful:              {self.stats['successful']} ({success_rate:.1f}%)")
        logger.info(f"✗ Failed:                  {self.stats['failed']}")
        logger.info(f"✗ Queue send failures:     {self.stats['queue_failures']}")

        # Get parsing service statistics
        parsing_stats = self.parsing_service.get_statistics()
        if parsing_stats['total_processed'] > 0:
            logger.info("PARSING SERVICE BREAKDOWN:")
            logger.info(f"  - Failed purification:   {parsing_stats['failed_purification']}")
            logger.info(f"  - Failed LLM processing: {parsing_stats['failed_llm_processing']}")
            logger.info(f"  - Failed verification:   {parsing_stats['failed_verification']}")

        logger.info("=" * 80)

    def run(self):
        """Main processing loop"""
        logger.info("Document Processor started - listening for messages...")
        last_stats_log = time.time()

        # Verify services are available
        if not self.parsing_service.is_available():
            logger.error("Parsing service is not available. Exiting.")
            return

        while True:
            try:
                # Receive message from processing queue
                message = self.queue_client.receive_message('processing', timeout=20)

                if message:
                    # Parse input data
                    try:
                        input_data = ProcessedData.from_dict(message)
                    except Exception as e:
                        logger.error(f"Error parsing input data: {e}")
                        continue

                    # Process the document
                    processed_data = self.process_document(input_data)

                    if processed_data:
                        # Send to embedding queue
                        success = self.queue_client.send_message('embedding', processed_data.to_dict())
                        if not success:
                            self.stats['queue_failures'] += 1
                            infoleg_id = processed_data.scraping_data.infoleg_response.infoleg_id
                            logger.error(f"Queue failure: Could not send document {infoleg_id} to embedding queue")

                # Log statistics every 5 minutes or after every 10 documents
                current_time = time.time()
                if (current_time - last_stats_log > 300) or (
                    self.stats['total_processed'] > 0
                    and self.stats['total_processed'] % 10 == 0
                ):
                    self.log_statistics()
                    last_stats_log = current_time

            except Exception as e:
                logger.error(f"Error in processing loop: {str(e)}")
                time.sleep(5)  # Wait before retrying


def main():
    """Main entry point"""
    logger.info("Starting processor service...")

    # Initialize processor
    processor = DocumentProcessor()

    try:
        # Run the processor
        processor.run()
    except KeyboardInterrupt:
        logger.info("Shutting down processor service...")


if __name__ == "__main__":
    main()