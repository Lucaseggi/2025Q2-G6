from abc import ABC, abstractmethod
from typing import Optional
import sys
import os

# Add the parent directory to import shared models
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import InfolegApiResponse


class NormProviderInterface(ABC):
    """Interface for norm provider operations"""

    @abstractmethod
    def get_norm_by_id(self, norm_id: int) -> Optional[InfolegApiResponse]:
        """
        Retrieve a specific norm by its ID

        Args:
            norm_id: ID of the norm to retrieve

        Returns:
            InfolegApiResponse object if found, None otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the data source is available

        Returns:
            True if data source is reachable, False otherwise
        """
        pass