import grpc
import os
import json
from datetime import datetime

# Import generated gRPC modules (these will be generated when container builds)
import relational_pb2
import relational_pb2_grpc
import vectorial_pb2
import vectorial_pb2_grpc


def remove_embedding(obj):
    """
    Recursively remove 'embedding' keys from dicts or lists.
    """
    if isinstance(obj, dict):
        obj.pop("embedding", None)
        for v in obj.values():
            remove_embedding(v)
    elif isinstance(obj, list):
        for v in obj:
            remove_embedding(v)
    return obj


class GrpcServiceClients:
    """Client wrapper for both relational-ms and vectorial-ms gRPC services"""

    def __init__(self):
        self.relational_host = os.getenv('RELATIONAL_MS_HOST', 'relational-ms')
        self.relational_port = os.getenv('RELATIONAL_MS_PORT', '50051')
        self.vectorial_host = os.getenv('VECTORIAL_MS_HOST', 'vectorial-ms')
        self.vectorial_port = os.getenv('VECTORIAL_MS_PORT', '50052')

        self.relational_address = f"{self.relational_host}:{self.relational_port}"
        self.vectorial_address = f"{self.vectorial_host}:{self.vectorial_port}"

        print(f"[{datetime.now()}] gRPC clients initialized:")
        print(f"[{datetime.now()}] - Relational MS: {self.relational_address}")
        print(f"[{datetime.now()}] - Vectorial MS: {self.vectorial_address}")

    def call_relational_store(self, data):
        """Call the relational-ms store method"""
        try:
            # If data is a dict/object, convert to JSON and clean embeddings
            if isinstance(data, dict):
                # Deep copy to avoid modifying original data
                import copy
                clean_data = copy.deepcopy(data)
                remove_embedding(clean_data)
                json_data = json.dumps(clean_data, default=str)
            elif isinstance(data, str):
                # If it's already a string, assume it's JSON and parse/clean/stringify
                try:
                    parsed_data = json.loads(data)
                    remove_embedding(parsed_data)
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
                    'service': 'relational-ms',
                    'success': response.success,
                    'message': response.message,
                    'pk_mapping_json': response.pk_mapping_json if hasattr(response, 'pk_mapping_json') else None
                }

        except Exception as e:
            error_msg = f"Failed to call relational-ms: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'relational-ms',
                'success': False,
                'message': error_msg
            }

    def call_vectorial_store(self, data, pk_mapping_json=None):
        """Call the vectorial-ms store method with original data (preserving embeddings)"""
        try:
            # For vectorial-ms, we need to send the original data with embeddings
            # The vectorial-ms will handle the PK mapping separately in future versions
            if isinstance(data, dict):
                json_data = json.dumps(data, default=str)
            elif isinstance(data, str):
                json_data = data
            else:
                json_data = str(data)

            with grpc.insecure_channel(self.vectorial_address) as channel:
                stub = vectorial_pb2_grpc.VectorialServiceStub(channel)
                request = vectorial_pb2.StoreRequest(data=json_data)
                response = stub.Store(request)

                print(f"[{datetime.now()}] Vectorial MS Response:")
                print(f"[{datetime.now()}] - Success: {response.success}")
                print(f"[{datetime.now()}] - Message: {response.message}")

                return {
                    'service': 'vectorial-ms',
                    'success': response.success,
                    'message': response.message
                }

        except Exception as e:
            error_msg = f"Failed to call vectorial-ms: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-ms',
                'success': False,
                'message': error_msg
            }

    def call_both_services_sequential(self, data):
        """Call relational-ms first, then vectorial-ms if successful (sequential pipeline)"""
        print(f"[{datetime.now()}] Starting sequential pipeline...")

        # Call relational service first
        relational_result = self.call_relational_store(data)

        if relational_result['success']:
            print(f"[{datetime.now()}] Relational storage successful, proceeding with vectorial storage...")

            # Call vectorial service with original data (preserving embeddings)
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
                'vectorial': {'service': 'vectorial-ms', 'success': False, 'message': 'Skipped due to relational failure'},
                'pipeline_success': False
            }