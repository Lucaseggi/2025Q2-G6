"""Queue worker for processing messages from scraping queue"""

import logging
import time
import sys
import os

sys.path.append('/app/shared')

from src.config.settings import get_settings
from src.dependencies import get_purifier_service
from failed_processing_logger import FailedProcessingLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PurifierWorker:
    """Worker for processing messages from scraping queue"""

    def __init__(self):
        """Initialize worker"""
        logger.info("Initializing Purifier Worker...")

        self.settings = get_settings()
        self.purifier = get_purifier_service()
        self.failed_logger = FailedProcessingLogger(service_name="purifier")

        # Access queue service through purifier
        self.queue = self.purifier.queue

        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'queue_failures': 0,
        }

        logger.info("Purifier Worker initialized successfully")

    def log_statistics(self):
        """Log current processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return

        success_rate = (self.stats['successful'] / total) * 100

        logger.info("=" * 80)
        logger.info("PURIFICATION STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total processed:           {total}")
        logger.info(f"✓ Successful:              {self.stats['successful']} ({success_rate:.1f}%)")
        logger.info(f"✗ Failed:                  {self.stats['failed']}")
        logger.info(f"✗ Queue send failures:     {self.stats['queue_failures']}")

        # Log failed processing summary
        failed_summary = self.failed_logger.get_summary()
        if failed_summary.get('unique_failed_ids', 0) > 0:
            logger.info("FAILED PROCESSING TRACKING:")
            logger.info(f"  - Unique failed IDs:     {failed_summary['unique_failed_ids']}")
            logger.info(f"  - Log file:              {self.failed_logger.log_file}")

        logger.info("=" * 80)

    def run(self):
        """Main processing loop"""
        logger.info("Purifier Worker started - listening for messages...")
        last_stats_log = time.time()

        while True:
            try:
                # Receive message from scraping queue
                message = self.queue.receive_message(
                    self.settings.rabbitmq.queues['input'],
                    timeout=20
                )

                if message:
                    self.stats['total_processed'] += 1

                    # Extract infoleg_id for failure tracking
                    try:
                        # Handle cache wrapper format
                        if 'cached_at' in message and 'data' in message:
                            actual_data = message['data']
                        else:
                            actual_data = message

                        infoleg_id = actual_data.get('scraping_data', {}).get('infoleg_response', {}).get('infoleg_id')
                    except Exception:
                        infoleg_id = None

                    # Process the message
                    success, result = self.purifier.process_from_queue(message)

                    if success:
                        self.stats['successful'] += 1
                    else:
                        self.stats['failed'] += 1
                        if 'queue_failed' in result:
                            self.stats['queue_failures'] += 1

                        # Log failure for manual intervention
                        if infoleg_id:
                            self.failed_logger.log_failure(
                                infoleg_id=infoleg_id,
                                error_type="purification_failed",
                                error_message=result,
                                stage="purification",
                                additional_data={"service": "purifier"}
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
                time.sleep(5)


def main():
    """Main entry point"""
    logger.info("Starting purifier worker service...")

    worker = PurifierWorker()

    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("Shutting down purifier worker service...")


if __name__ == "__main__":
    main()
