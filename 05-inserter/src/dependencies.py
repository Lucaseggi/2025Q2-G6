"""
Dependency injection for inserter service.

This module provides factory functions for creating service instances with proper configuration.
All environment logic is contained in Settings - business logic never accesses environment directly.
"""

import sys
import os
from functools import lru_cache

# Add paths for imports
sys.path.append('/var/task')
sys.path.append('/var/task/shared')
sys.path.append('/app')
sys.path.append('/app/shared')
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.config.settings import Settings, get_inserter_settings as _get_inserter_settings
from rest_storage_client import RestStorageClient
from storage_client_interface import StorageClientInterface


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)"""
    return _get_inserter_settings()


def get_storage_client() -> StorageClientInterface:
    """
    Factory function to create storage client based on settings.

    Returns:
        StorageClientInterface: Configured storage client (REST or gRPC)
    """
    settings = get_settings()

    client_type = settings.storage.default_client_type

    if client_type == "rest":
        # Create REST client with API URLs from settings
        return RestStorageClient(
            relational_api_url=settings.api_endpoints.relational_api_url,
            vectorial_api_url=settings.api_endpoints.vectorial_api_url,
            timeout_seconds=settings.storage.timeout_seconds
        )
    elif client_type == "grpc":
        # Import here to avoid import errors if proto files not available
        from grpc_storage_client import GrpcStorageClient

        # Note: For Lambda, gRPC won't work directly - guards are exposed via API Gateway
        # This branch is for local development only
        raise NotImplementedError(
            "gRPC client not supported in Lambda deployment. "
            "Guards are exposed via API Gateway REST endpoints. "
            "Set storage.default_client_type to 'rest' in config.json"
        )
    else:
        raise ValueError(f"Unknown storage client type: {client_type}")
