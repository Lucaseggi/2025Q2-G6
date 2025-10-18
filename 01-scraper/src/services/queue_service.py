import sys
import os
import logging
from typing import Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from sqs_client import SQSClient

from ..interfaces.queue_interface import QueueInterface
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class QueueService(QueueInterface):
    """SQS-based queue service implementation"""

    def __init__(self, settings: Settings):
        """Initialize queue service with SQS backend"""
        self.settings = settings
        self._client = None

    @property
    def client(self) -> SQSClient:
        """Lazy initialization of SQS client"""
        if self._client is None:
            # Set environment variables for SQSClient
            if self.settings.sqs.endpoint:
                os.environ['SQS_ENDPOINT'] = self.settings.sqs.endpoint
            os.environ['AWS_DEFAULT_REGION'] = self.settings.sqs.region

            # Set queue URLs from settings
            output_queue = self.settings.sqs.queues.get('output', '')
            os.environ['PURIFYING_QUEUE_URL'] = f"{self.settings.sqs.endpoint}/000000000000/{output_queue}"

            self._client = SQSClient()
        return self._client

    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Send a message to the specified queue"""
        try:
            return self.client.send_message(queue_name, message)
        except Exception as e:
            logger.error(f"Error sending message to queue {queue_name}: {e}")
            return False

    def connect(self) -> bool:
        """Establish connection to the message queue"""
        try:
            # SQSClient is connectionless
            return True
        except Exception as e:
            logger.error(f"Error connecting to SQS: {e}")
            return False

    def disconnect(self) -> bool:
        """Close connection to the message queue"""
        try:
            if self._client:
                self._client.close()
                self._client = None
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from SQS: {e}")
            return False