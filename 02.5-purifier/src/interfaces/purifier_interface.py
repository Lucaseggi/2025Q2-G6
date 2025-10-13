from abc import ABC, abstractmethod
from typing import Tuple


class PurifierInterface(ABC):
    """Interface for purifier service"""

    @abstractmethod
    def replay_norm(self, norm_id: int, force: bool = False) -> Tuple[bool, str]:
        """Replay a norm from cache to the purification queue"""
        pass

    @abstractmethod
    def is_cached(self, norm_id: int) -> bool:
        """Check if a norm is cached"""
        pass
