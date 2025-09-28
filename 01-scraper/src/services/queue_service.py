import sys
import os
import logging
from typing import Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from rabbitmq_client import RabbitMQClient

from ..interfaces.queue_interface import QueueInterface
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class QueueService(QueueInterface):
    """RabbitMQ-based queue service implementation"""

    def __init__(self, settings: Settings):
        """Initialize queue service with RabbitMQ backend"""
        self.settings = settings
        self._client = None

    @property
    def client(self) -> RabbitMQClient:
        """Lazy initialization of RabbitMQ client"""
        if self._client is None:
            # Set environment variables for RabbitMQClient
            os.environ['RABBITMQ_HOST'] = self.settings.rabbitmq.host
            os.environ['RABBITMQ_PORT'] = str(self.settings.rabbitmq.port)
            os.environ['RABBITMQ_USER'] = self.settings.rabbitmq.user
            os.environ['RABBITMQ_PASSWORD'] = self.settings.rabbitmq.password
            os.environ['RABBITMQ_VHOST'] = self.settings.rabbitmq.vhost

            self._client = RabbitMQClient()
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
            # RabbitMQClient handles connection internally
            return True
        except Exception as e:
            logger.error(f"Error connecting to RabbitMQ: {e}")
            return False

    def disconnect(self) -> bool:
        """Close connection to the message queue"""
        try:
            if self._client:
                # RabbitMQClient doesn't expose disconnect, but we can reset
                self._client = None
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
            return False