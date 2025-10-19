"""REST API-based implementation of the storage client interface."""

import os
import json
import copy
import requests
from datetime import datetime
from typing import Any, Dict

from storage_client_interface import StorageClientInterface
from data_enrichment_service import DataEnrichmentService, MissingIdError


class RestStorageClient(StorageClientInterface):
    """REST API-based client for communicating with relational and vectorial services."""

    def __init__(self):
        self.relational_base_url = os.getenv('RELATIONAL_API_HOST', 'http://localhost:8090')
        self.vectorial_base_url = os.getenv('VECTORIAL_API_HOST', 'http://localhost:8080')

        # Remove trailing slashes
        self.relational_base_url = self.relational_base_url.rstrip('/')
        self.vectorial_base_url = self.vectorial_base_url.rstrip('/')

        print(f"[{datetime.now()}] REST clients initialized:")
        print(f"[{datetime.now()}] - Relational API: {self.relational_base_url}")
        print(f"[{datetime.now()}] - Vectorial API: {self.vectorial_base_url}")

    def call_relational_store(self, data: Any) -> Dict[str, Any]:
        """Call the relational API store method via REST"""
        try:
            # If data is a dict/object, convert to clean format
            if isinstance(data, dict):
                # Deep copy to avoid modifying original data
                clean_data = copy.deepcopy(data)
                DataEnrichmentService.remove_embedding(clean_data)
                payload = clean_data
            elif isinstance(data, str):
                # If it's already a string, parse it
                try:
                    parsed_data = json.loads(data)
                    DataEnrichmentService.remove_embedding(parsed_data)
                    payload = parsed_data
                except json.JSONDecodeError:
                    # If it's not valid JSON, wrap it
                    payload = {"data": data}
            else:
                # For other types, wrap in dict
                payload = {"data": str(data)}

            url = f"{self.relational_base_url}/api/v1/relational/store"

            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            response_data = response.json()

            print(f"[{datetime.now()}] Relational API Response:")
            print(f"[{datetime.now()}] - Success: {response_data.get('success')}")
            print(f"[{datetime.now()}] - Message: {response_data.get('message')}")

            return {
                'service': 'relational-api',
                'success': response_data.get('success', False),
                'message': response_data.get('message', ''),
                'pk_mapping_json': response_data.get('pkMappingJson')  # API returns camelCase
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to call relational API: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'relational-api',
                'success': False,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error calling relational API: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'relational-api',
                'success': False,
                'message': error_msg
            }

    def call_vectorial_store(self, data: Any, pk_mapping_json: Any = None) -> Dict[str, Any]:
        """Call the vectorial API store method via REST with original data (preserving embeddings)"""
        try:
            # Enrich data with IDs from relational DB
            enriched_data = DataEnrichmentService.enrich_data_with_ids(data, pk_mapping_json)

            # Convert to payload format
            if isinstance(enriched_data, dict):
                payload = enriched_data
            elif isinstance(enriched_data, str):
                payload = json.loads(enriched_data)
            else:
                payload = {"data": str(enriched_data)}

            url = f"{self.vectorial_base_url}/api/v1/vectorial/store"

            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            response_data = response.json()

            print(f"[{datetime.now()}] Vectorial API Response:")
            print(f"[{datetime.now()}] - Success: {response_data.get('success')}")
            print(f"[{datetime.now()}] - Message: {response_data.get('message')}")

            return {
                'service': 'vectorial-api',
                'success': response_data.get('success', False),
                'message': response_data.get('message', '')
            }

        except MissingIdError as e:
            error_msg = f"ID enrichment failed: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-api',
                'success': False,
                'message': error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to call vectorial API: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-api',
                'success': False,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error calling vectorial API: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-api',
                'success': False,
                'message': error_msg
            }
