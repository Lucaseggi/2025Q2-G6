"""Interface for parsing services"""

from abc import ABC, abstractmethod
from typing import Optional
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from models import ProcessedData


class ParsingServiceInterface(ABC):
    """Interface for document parsing services"""

    @abstractmethod
    def process_document(self, input_data: ProcessedData) -> Optional[ProcessedData]:
        """
        Process a document through the complete parsing pipeline

        Args:
            input_data: ProcessedData containing scraping data

        Returns:
            ProcessedData with processing_data populated, or None if processing fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the parsing service is available

        Returns:
            True if service is available, False otherwise
        """
        pass