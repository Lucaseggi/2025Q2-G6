"""Queue worker for the processor service"""

import sys
import time
import os
from typing import Optional

# Add shared modules to path
sys.path.append('/app/shared')
from rabbitmq_client import RabbitMQClient
from models import ProcessedData
from structured_logger import StructuredLogger, LogStage
from failed_processing_logger import FailedProcessingLogger

# Add local src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from services.parsing_service import ParsingService
from services.text_processing_service import TextProcessingService
from services.llm_service import LLMService
from services.verification_service import VerificationService
from services.storage_service import StorageService

from config import ProcessorSettings

logger = StructuredLogger("processor", "worker")


class DocumentProcessor:
    """Main document processor with clean architecture"""

    def __init__(self):
        """Initialize document processor with dependency injection"""
        logger.info("Initializing Document Processor", stage=LogStage.STARTUP)

        # Load configuration
        self.config = ProcessorSettings()

        # Initialize shared components
        self.queue_client = RabbitMQClient()
        self.failed_logger = FailedProcessingLogger(service_name="processor")

        # Initialize services with dependency injection
        self.text_processor = TextProcessingService()
        self.llm_service = LLMService(self.config)
        self.verification_service = VerificationService(
            similarity_threshold=getattr(self.config.gemini, 'diff_threshold', 0.15)
        )
        self.storage_service = StorageService(
            bucket_name=self.config.s3.bucket_name,
            endpoint_url=self.config.s3.endpoint,
            access_key_id=self.config.s3.access_key_id,
            secret_access_key=self.config.s3.secret_access_key,
            region=self.config.s3.region
        )

        # Initialize main parsing service
        self.parsing_service = ParsingService(
            text_processor=self.text_processor,
            llm_service=self.llm_service,
            verification_service=self.verification_service,
            storage_service=self.storage_service
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

                # Log failure for manual intervention
                self.failed_logger.log_failure(
                    infoleg_id=infoleg_id,
                    error_type="processing_failed",
                    error_message="Processing pipeline returned None",
                    stage="processing",
                    additional_data={"service": "processor"}
                )
                return None

        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Error processing document: {e}")

            # Log failure with exception details
            if 'infoleg_id' in locals():
                self.failed_logger.log_failure(
                    infoleg_id=infoleg_id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stage="processing_exception",
                    additional_data={"service": "processor"}
                )
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
            logger.info(f"  - Stored to S3:          {parsing_stats['stored_to_s3']}")

        # Log failed processing summary
        failed_summary = self.failed_logger.get_summary()
        if failed_summary.get('unique_failed_ids', 0) > 0:
            logger.info("FAILED PROCESSING TRACKING:")
            logger.info(f"  - Unique failed IDs:     {failed_summary['unique_failed_ids']}")
            logger.info(f"  - Log file:              {self.failed_logger.log_file}")

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
                        # Handle cache wrapper format
                        if 'cached_at' in message and 'data' in message:
                            # Data comes from cache, unwrap it
                            actual_data = message['data']
                        else:
                            # Data is direct ProcessedData format
                            actual_data = message

                        input_data = ProcessedData.from_dict(actual_data)
                        infoleg_id = input_data.scraping_data.infoleg_response.infoleg_id

                        logger.log_message_received(
                            queue_name='processing',
                            infoleg_id=infoleg_id
                        )
                    except Exception as e:
                        logger.error(f"Error parsing input data: {str(e)}", stage=LogStage.QUEUE_ERROR)
                        continue

                    # Process the document
                    processed_data = self.process_document(input_data)

                    if processed_data:
                        infoleg_id = processed_data.scraping_data.infoleg_response.infoleg_id
                        # Send to embedding queue
                        success = self.queue_client.send_message('embedding', processed_data.to_dict())
                        if success:
                            logger.log_message_sent(
                                queue_name='embedding',
                                infoleg_id=infoleg_id
                            )
                        else:
                            self.stats['queue_failures'] += 1
                            logger.error(
                                "Failed to send to embedding queue",
                                stage=LogStage.QUEUE_ERROR,
                                infoleg_id=infoleg_id
                            )

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