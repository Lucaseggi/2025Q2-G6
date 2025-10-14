from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class QueueInterface(ABC):
    """Interface for queue operations"""

    @abstractmethod
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Send message to queue"""
        pass

    @abstractmethod
    def receive_message(self, queue_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Receive message from queue"""
        pass
