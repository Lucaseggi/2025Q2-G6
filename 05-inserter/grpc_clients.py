"""
Backward compatibility module.
This module is deprecated. Use grpc_storage_client.py or rest_storage_client.py instead.
"""

# For backward compatibility, import the new class with the old name
from grpc_storage_client import GrpcStorageClient as GrpcServiceClients
from data_enrichment_service import MissingIdError, DataEnrichmentService

# Re-export for backward compatibility
remove_embedding = DataEnrichmentService.remove_embedding

__all__ = ['GrpcServiceClients', 'MissingIdError', 'remove_embedding']
