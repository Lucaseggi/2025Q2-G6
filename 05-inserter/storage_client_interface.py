"""Abstract interface for storage clients (gRPC, REST, etc.)."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class StorageClientInterface(ABC):
    """Interface for clients that communicate with relational and vectorial storage services."""

    @abstractmethod
    def call_relational_store(self, data: Any) -> Dict[str, Any]:
        """
        Store data in the relational service.

        Args:
            data: The data to store (dict or JSON string)

        Returns:
            dict with keys: service, success, message, pk_mapping_json (optional)
        """
        pass

    @abstractmethod
    def call_vectorial_store(self, data: Any, pk_mapping_json: Any = None) -> Dict[str, Any]:
        """
        Store data in the vectorial service.

        Args:
            data: The data to store (dict or JSON string)
            pk_mapping_json: PK mapping from relational storage for ID enrichment

        Returns:
            dict with keys: service, success, message
        """
        pass

    def call_both_services_sequential(self, data: Any) -> Dict[str, Any]:
        """
        Call relational service first, then vectorial service if successful.

        Args:
            data: The data to store

        Returns:
            dict with keys: relational, vectorial, pipeline_success
        """
        from datetime import datetime

        print(f"[{datetime.now()}] Starting sequential pipeline...")

        # Call relational service first
        relational_result = self.call_relational_store(data)

        if relational_result['success']:
            print(f"[{datetime.now()}] Relational storage successful, proceeding with vectorial storage...")

            # Call vectorial service with pk_mapping_json
            vectorial_result = self.call_vectorial_store(data, relational_result.get('pk_mapping_json'))

            return {
                'relational': relational_result,
                'vectorial': vectorial_result,
                'pipeline_success': vectorial_result['success']
            }
        else:
            print(f"[{datetime.now()}] Relational storage failed, skipping vectorial storage")
            return {
                'relational': relational_result,
                'vectorial': {'service': 'vectorial-guard', 'success': False, 'message': 'Skipped due to relational failure'},
                'pipeline_success': False
            }
