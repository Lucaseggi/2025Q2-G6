from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class CacheInterface(ABC):
    """Interface for cache operations"""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache by key

        Args:
            key: Cache key to retrieve

        Returns:
            Cached data if found, None otherwise
        """
        pass

    @abstractmethod
    def put(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Store data in cache with the given key (overwrites if exists)

        Args:
            key: Cache key to store under
            data: Data to cache

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache without retrieving data

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete data from cache by key

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        pass