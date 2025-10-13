"""Queue processor for embedding service"""

import json
import time
from datetime import datetime

# Add shared models to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from rabbitmq_client import RabbitMQClient
from models import ProcessedData
from structured_logger import StructuredLogger, LogStage

# Add src to path for services
sys.path.append(os.path.join(os.path.dirname(__file__)))
from interfaces.embedder_service_interface import EmbedderServiceInterface

logger = StructuredLogger("embedder", "worker")


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
        logger.info("Queue processor started - listening for messages", stage=LogStage.STARTUP)

        while True:
            try:
                # Receive message from embedding queue
                message_body = self.queue_client.receive_message('embedding', timeout=20)

                if message_body:
                    self.stats['total_processed'] += 1
                    start_time = time.time()

                    # Handle cache wrapper format
                    if 'cached_at' in message_body and 'data' in message_body:
                        actual_data = message_body['data']
                    else:
                        actual_data = message_body

                    # Parse the ProcessedData
                    input_data = ProcessedData.from_dict(actual_data)
                    norma_id = input_data.scraping_data.infoleg_response.infoleg_id

                    logger.log_message_received(
                        queue_name='embedding',
                        infoleg_id=norma_id
                    )

                    logger.log_processing_start(infoleg_id=norma_id)

                    # Process the document
                    processed_data = self.embedder_service.process_document(input_data)

                    if processed_data:
                        # Send the complete ProcessedData to inserting queue
                        success = self.queue_client.send_message('inserting', processed_data.to_dict())

                        if success:
                            self.stats['successful'] += 1
                            duration_ms = (time.time() - start_time) * 1000

                            logger.log_message_sent(
                                queue_name='inserting',
                                infoleg_id=norma_id
                            )

                            logger.log_processing_complete(
                                infoleg_id=norma_id,
                                duration_ms=duration_ms
                            )
                        else:
                            self.stats['queue_failures'] += 1
                            logger.error(
                                "Failed to send to inserting queue",
                                stage=LogStage.QUEUE_ERROR,
                                infoleg_id=norma_id
                            )
                    else:
                        self.stats['failed'] += 1
                        logger.log_processing_failed(
                            infoleg_id=norma_id,
                            error="Embedding generation failed"
                        )

                    # Log statistics every 100 documents or 5 minutes
                    if self.stats['total_processed'] % 100 == 0 or self.stats['total_processed'] % 20 == 0:
                        self._log_statistics()

            except Exception as e:
                logger.error(
                    f"Error in processing loop: {str(e)}",
                    stage=LogStage.QUEUE_ERROR,
                    error_type=type(e).__name__
                )
                time.sleep(5)

    def _log_statistics(self):
        """Log processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return

        success_rate = (self.stats['successful'] / total) * 100

        logger.log_statistics({
            'total_processed': total,
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'queue_failures': self.stats['queue_failures'],
            'success_rate': success_rate
        })