from abc import ABC, abstractmethod
from typing import Tuple


class ScraperInterface(ABC):
    """Interface for scraper service operations"""

    @abstractmethod
    def scrape_specific_norm(self, norm_id: int, force: bool = False) -> Tuple[bool, str]:
        """
        Scrape a specific norm by its ID

        Args:
            norm_id: ID of the norm to scrape
            force: Whether to force fresh scraping (bypass cache)

        Returns:
            Tuple of (success: bool, source: str)
            - success: True if operation succeeded
            - source: "cache", "scraped", or error description
        """
        pass

    @abstractmethod
    def is_cached(self, norm_id: int) -> bool:
        """
        Check if a norm is cached

        Args:
            norm_id: ID of the norm to check

        Returns:
            True if norm is cached, False otherwise
        """
        pass