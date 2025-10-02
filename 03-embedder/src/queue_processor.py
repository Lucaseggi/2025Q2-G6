"""Queue processor for embedding service"""

import json
import logging
import time
from datetime import datetime

# Add shared models to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from rabbitmq_client import RabbitMQClient
from models import ProcessedData

# Add src to path for services
sys.path.append(os.path.join(os.path.dirname(__file__)))
from interfaces.embedder_service_interface import EmbedderServiceInterface

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processes documents from the embedding queue"""

    def __init__(self, embedder_service: EmbedderServiceInterface):
        """
        Initialize queue processor.

        Args:
            embedder_service: The embedder service implementation
        """
        self.embedder_service = embedder_service
        self.queue_client = RabbitMQClient()
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'queue_failures': 0,
        }

    def process_documents_from_queue(self):
        """Main processing loop - listen for documents and process them"""
        logger.info("Queue processor started - listening for messages...")

        while True:
            try:
                # Receive message from embedding queue
                message_body = self.queue_client.receive_message('embedding', timeout=20)

                if message_body:
                    self.stats['total_processed'] += 1
                    logger.info("Received message for processing")

                    # Handle cache wrapper format
                    if 'cached_at' in message_body and 'data' in message_body:
                        # Data comes from cache, unwrap it
                        actual_data = message_body['data']
                        logger.debug(f"Processing cached data from {message_body.get('cached_at')}")
                    else:
                        # Data is direct ProcessedData format
                        actual_data = message_body

                    # Parse the ProcessedData
                    input_data = ProcessedData.from_dict(actual_data)
                    norma_id = input_data.scraping_data.infoleg_response.infoleg_id

                    # Process the document
                    processed_data = self.embedder_service.process_document(input_data)

                    if processed_data:
                        # Send the complete ProcessedData to inserting queue
                        success = self.queue_client.send_message('inserting', processed_data.to_dict())

                        if success:
                            self.stats['successful'] += 1
                            logger.info(f"Successfully processed and sent document {norma_id} to inserting queue")
                        else:
                            self.stats['queue_failures'] += 1
                            logger.error(f"Failed to send document {norma_id} to inserting queue")
                    else:
                        self.stats['failed'] += 1
                        logger.error(f"Failed to process document {norma_id}")

                    # Log statistics every 100 documents or 5 minutes
                    if self.stats['total_processed'] % 100 == 0 or self.stats['total_processed'] % 20 == 0:
                        self._log_statistics()
                else:
                    # No need to log timeout - it's normal behavior
                    pass

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(5)

    def _log_statistics(self):
        """Log processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return

        success_rate = (self.stats['successful'] / total) * 100

        logger.info("=== EMBEDDING PROCESSOR STATISTICS ===")
        logger.info(f"Total processed: {total}")
        logger.info(f"Successful: {self.stats['successful']} ({success_rate:.1f}%)")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Queue failures: {self.stats['queue_failures']}")
        logger.info("=" * 40)