"""gRPC-based implementation of the storage client interface."""

import grpc
import os
import json
import copy
from datetime import datetime
from typing import Any, Dict

# Import generated gRPC modules (these will be generated when container builds)
import relational_pb2
import relational_pb2_grpc
import vectorial_pb2
import vectorial_pb2_grpc

from storage_client_interface import StorageClientInterface
from data_enrichment_service import DataEnrichmentService, MissingIdError


class GrpcStorageClient(StorageClientInterface):
    """gRPC-based client for communicating with relational and vectorial services."""

    def __init__(self):
        self.relational_host = os.getenv('RELATIONAL_MS_HOST', 'relational-guard')
        self.relational_port = os.getenv('RELATIONAL_MS_PORT', '50051')
        self.vectorial_host = os.getenv('VECTORIAL_MS_HOST', 'vectorial-guard')
        self.vectorial_port = os.getenv('VECTORIAL_MS_PORT', '50052')

        self.relational_address = f"{self.relational_host}:{self.relational_port}"
        self.vectorial_address = f"{self.vectorial_host}:{self.vectorial_port}"

        print(f"[{datetime.now()}] gRPC clients initialized:")
        print(f"[{datetime.now()}] - Relational MS: {self.relational_address}")
        print(f"[{datetime.now()}] - Vectorial MS: {self.vectorial_address}")

    def call_relational_store(self, data: Any) -> Dict[str, Any]:
        """Call the relational-guard store method via gRPC"""
        try:
            # If data is a dict/object, convert to JSON and clean embeddings
            if isinstance(data, dict):
                # Deep copy to avoid modifying original data
                clean_data = copy.deepcopy(data)
                DataEnrichmentService.remove_embedding(clean_data)
                json_data = json.dumps(clean_data, default=str)
            elif isinstance(data, str):
                # If it's already a string, assume it's JSON and parse/clean/stringify
                try:
                    parsed_data = json.loads(data)
                    DataEnrichmentService.remove_embedding(parsed_data)
                    json_data = json.dumps(parsed_data, default=str)
                except json.JSONDecodeError:
                    # If it's not valid JSON, use as-is (for backward compatibility)
                    json_data = data
            else:
                # For other types, convert to string
                json_data = str(data)

            with grpc.insecure_channel(self.relational_address) as channel:
                stub = relational_pb2_grpc.RelationalServiceStub(channel)
                request = relational_pb2.StoreRequest(data=json_data)

                response = stub.Store(request)

                print(f"[{datetime.now()}] Relational MS Response:")
                print(f"[{datetime.now()}] - Success: {response.success}")
                print(f"[{datetime.now()}] - Message: {response.message}")

                return {
                    'service': 'relational-guard',
                    'success': response.success,
                    'message': response.message,
                    'pk_mapping_json': response.pk_mapping_json if hasattr(response, 'pk_mapping_json') else None
                }

        except Exception as e:
            error_msg = f"Failed to call relational-guard: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'relational-guard',
                'success': False,
                'message': error_msg
            }

    def call_vectorial_store(self, data: Any, pk_mapping_json: Any = None) -> Dict[str, Any]:
        """Call the vectorial-guard store method via gRPC with original data (preserving embeddings)"""
        try:
            # Enrich data with IDs from relational DB
            enriched_data = DataEnrichmentService.enrich_data_with_ids(data, pk_mapping_json)

            # Convert to JSON
            if isinstance(enriched_data, dict):
                json_data = json.dumps(enriched_data, default=str)
            elif isinstance(enriched_data, str):
                json_data = enriched_data
            else:
                json_data = str(enriched_data)

            with grpc.insecure_channel(self.vectorial_address) as channel:
                stub = vectorial_pb2_grpc.VectorialServiceStub(channel)
                request = vectorial_pb2.StoreRequest(data=json_data)
                response = stub.Store(request)

                print(f"[{datetime.now()}] Vectorial MS Response:")
                print(f"[{datetime.now()}] - Success: {response.success}")
                print(f"[{datetime.now()}] - Message: {response.message}")

                return {
                    'service': 'vectorial-guard',
                    'success': response.success,
                    'message': response.message
                }

        except MissingIdError as e:
            error_msg = f"ID enrichment failed: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-guard',
                'success': False,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Failed to call vectorial-guard: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-guard',
                'success': False,
                'message': error_msg
            }


# Backward compatibility - keep the old class name as an alias
GrpcServiceClients = GrpcStorageClient
