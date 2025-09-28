"""Interface for text processing services"""

from abc import ABC, abstractmethod
from typing import Optional


class TextProcessingInterface(ABC):
    """Interface for text processing services"""

    @abstractmethod
    def purify_text(self, text: str) -> Optional[str]:
        """
        Clean and purify raw text content

        Args:
            text: Raw text to process

        Returns:
            Purified text or None if processing fails
        """
        pass

    @abstractmethod
    def is_valid_text(self, text: str) -> bool:
        """
        Check if text is valid for processing

        Args:
            text: Text to validate

        Returns:
            True if text is valid, False otherwise
        """
        pass