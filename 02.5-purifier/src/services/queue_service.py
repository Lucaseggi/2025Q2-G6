import sys
import os
import logging
from typing import Dict, Any, Optional

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

    def receive_message(self, queue_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Receive a message from the specified queue"""
        try:
            return self.client.receive_message(queue_name, timeout=timeout)
        except Exception as e:
            logger.error(f"Error receiving message from queue {queue_name}: {e}")
            return None
