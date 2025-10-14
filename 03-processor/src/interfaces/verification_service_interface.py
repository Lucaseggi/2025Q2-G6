"""Interface for verification services"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class VerificationServiceInterface(ABC):
    """Interface for response verification services"""

    @abstractmethod
    def verify_structured_response(self, original_text: str, structured_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify that structured data accurately represents the original text

        Args:
            original_text: The original text that was processed
            structured_data: The structured data extracted from the text

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def calculate_similarity_score(self, original_text: str, structured_data: Dict[str, Any]) -> float:
        """
        Calculate similarity score between original text and structured data

        Args:
            original_text: The original text
            structured_data: The structured data

        Returns:
            Similarity score between 0.0 and 1.0
        """
        pass