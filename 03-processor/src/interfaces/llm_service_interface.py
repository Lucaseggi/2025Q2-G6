"""Interface for LLM processing services"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result of LLM processing"""
    success: bool
    structured_data: Optional[Dict[str, Any]] = None
    model_used: str = ""
    processing_time: float = 0.0
    error_message: Optional[str] = None
    tokens_used: int = 0
    json_validation_passed: bool = False
    json_validation_error: Optional[str] = None


class LLMServiceInterface(ABC):
    """Interface for LLM processing services"""

    @abstractmethod
    def process_text(self, text: str) -> ProcessingResult:
        """
        Process text using LLM to extract structured data

        Args:
            text: The text to process

        Returns:
            ProcessingResult with structured data and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM service is available

        Returns:
            True if service is available, False otherwise
        """
        pass