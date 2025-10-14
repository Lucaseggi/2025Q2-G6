"""Storage service interface for processor"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class StorageInterface(ABC):
    """Interface for storage operations"""

    @abstractmethod
    def store(self, key: str, data: Dict[str, Any]) -> bool:
        """Store data with the given key (overwrites if exists)"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in storage"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from storage by key"""
        pass
