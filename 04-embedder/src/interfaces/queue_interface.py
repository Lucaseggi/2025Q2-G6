from abc import ABC, abstractmethod
from typing import Dict, Any


class QueueInterface(ABC):
    """Interface for message queue operations"""

    @abstractmethod
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to the specified queue

        Args:
            queue_name: Name of the queue to send to
            message: Message data to send

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the message queue

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to the message queue

        Returns:
            True if successful, False otherwise
        """
        pass