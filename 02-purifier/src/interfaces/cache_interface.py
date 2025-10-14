from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class CacheInterface(ABC):
    """Interface for cache operations"""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache"""
        pass

    @abstractmethod
    def put(self, key: str, data: Dict[str, Any]) -> bool:
        """Store data in cache"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from cache"""
        pass
