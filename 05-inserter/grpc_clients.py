import grpc
import os
import json
from datetime import datetime

# Import generated gRPC modules (these will be generated when container builds)
import relational_pb2
import relational_pb2_grpc
import vectorial_pb2
import vectorial_pb2_grpc
from types import SimpleNamespace

class MissingIdError(Exception):
    """Custom exception when a division or article has no ID."""
    pass

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
    """Client wrapper for both relational-guard and vectorial-guard gRPC services"""

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

    def call_relational_store(self, data):
        """Call the relational-guard store method"""
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

                # with open("./sample_files/relational-response.json", "r", encoding="utf-8") as f:
                #     response = SimpleNamespace(
                #         message="Success",
                #         success="YEP",
                #         pk_mapping_json=json.load(f)
                #     )

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

    def _enrich_divisions_recursive(self, divisions, division_pks, article_pks, parent_key=""):
        """
        Recursively enrich divisions and their nested articles/divisions with IDs.
        Uses 'order' field to build the hierarchical key.
        """
        if not divisions:
            return

        for division in divisions:
            division_order = division.get('order')
            if division_order is not None:
                division_key = f"{parent_key}d{division_order}" if parent_key is "" else f"{parent_key}_d{division_order}"

                if division_key in division_pks:
                    division['id'] = division_pks[division_key]
                    print(f"[{datetime.now()}] - Enriched division (order={division_order}) with key '{division_key}' and ID: {division['id']}")

                if 'articles' in division and division['articles']:
                    self._enrich_articles_recursive(division['articles'], article_pks, division_key)

                if 'divisions' in division and division['divisions']:
                    self._enrich_divisions_recursive(division['divisions'], division_pks, article_pks, division_key + "_")

    def _enrich_articles_recursive(self, articles, article_pks, parent_key=""):
        """
        Recursively enrich articles and their nested articles with IDs.
        Uses 'order' field to build the hierarchical key.
        """
        if not articles:
            return

        for article in articles:
            article_order = article.get('order')
            if article_order is not None:
                article_key = f"{parent_key}_a{article_order}"

                if article_key in article_pks:
                    article['id'] = article_pks[article_key]
                    print(f"[{datetime.now()}] - Enriched article (order={article_order}) with key '{article_key}' and ID: {article['id']}")

                if 'articles' in article and article['articles']:
                    self._enrich_articles_recursive(article['articles'], article_pks, article_key)

    def enrich_data_with_ids(self, data, pk_mapping_json):
        """
        Enrich the data with IDs from pk_mapping_json.
        Adds 'id' field to each article and division based on the relational DB IDs.
        Handles nested divisions and articles recursively.
        Format: {"normaId": int, "divisionPks": {key: id}, "articlePks": {key: id}}
        Keys like "d5_a1_a2" represent article 2 within article 1 within division 5.
        """
        if not pk_mapping_json:
            print(f"[{datetime.now()}] - No pk_mapping_json provided, skipping ID enrichment")
            return data

        try:
            pk_mapping = json.loads(pk_mapping_json) if isinstance(pk_mapping_json, str) else pk_mapping_json

            if isinstance(data, str):
                data_obj = json.loads(data)
            else:
                import copy
                data_obj = copy.deepcopy(data)

            structured_norma = (
                data_obj
                .get("data", {})
                .get("norma", {})
                .get("structured_texto_norma", None)
            )

            if 'normaId' in pk_mapping:
                if structured_norma is not None:
                    structured_norma['norma_id'] = pk_mapping['normaId']
                    print(f"[{datetime.now()}] - Enriched norma with ID: {pk_mapping['normaId']}")
                else:
                    print(f"[{datetime.now()}] - WARNING: structured_texto_norma not found, norma_id not inserted")

            division_pks = pk_mapping.get('divisionPks', {})
            article_pks = pk_mapping.get('articlePks', {})

            if structured_norma and 'divisions' in structured_norma:
                self._enrich_divisions_recursive(structured_norma['divisions'], division_pks, article_pks)
                self._validate_ids_recursive(structured_norma['divisions'])

            return data_obj

        except json.JSONDecodeError as e:
            print(f"[{datetime.now()}] - Error parsing data for enrichment: {e}")
            return data
        except Exception as e:
            print(f"[{datetime.now()}] - Error enriching data with IDs: {e}")
            return data

    def _validate_ids_recursive(self, divisions, parent_path="root"):
        """
        Recursively validate that every division and article has an 'id'.
        Raises MissingIdError if any 'id' is missing.
        """
        if not divisions:
            return

        for division in divisions:
            division_order = division.get('order', 'unknown')
            division_path = f"{parent_path}.division(order={division_order})"

            if 'id' not in division or division['id'] is None:
                raise MissingIdError(
                    f"Missing ID in {division_path}"
                )

            # Validate articles under this division
            if 'articles' in division and division['articles']:
                for article in division['articles']:
                    article_order = article.get('order', 'unknown')
                    article_path = f"{division_path}.article(order={article_order})"

                    if 'id' not in article or article['id'] is None:
                        raise MissingIdError(
                            f"Missing ID in {article_path}"
                        )

                    # Recurse into nested articles
                    if 'articles' in article and article['articles']:
                        self._validate_articles_recursive(article['articles'], article_path)

            # Validate nested divisions
            if 'divisions' in division and division['divisions']:
                self._validate_ids_recursive(division['divisions'], parent_path=division_path)


    def _validate_articles_recursive(self, articles, parent_path="article"):
        """
        Recursively validate that every nested article has an 'id'.
        """
        if not articles:
            return

        for article in articles:
            article_order = article.get('order', 'unknown')
            article_path = f"{parent_path}.article(order={article_order})"

            if 'id' not in article or article['id'] is None:
                raise MissingIdError(
                    f"Missing ID in {article_path}"
                )

            if 'articles' in article and article['articles']:
                self._validate_articles_recursive(article['articles'], parent_path=article_path)


    def call_vectorial_store(self, data, pk_mapping_json=None):
        """Call the vectorial-guard store method with original data (preserving embeddings)"""
        try:
            # Enrich data with IDs from relational DB
            enriched_data = self.enrich_data_with_ids(data, pk_mapping_json)

            # remove_embedding(enriched_data)
            # print("ENRICHED DATA:", json.dumps(shorten(enriched_data), indent=2, ensure_ascii=False))
            # return {
            #         'service': 'vectorial-guard',
            #         'success': "DUMMY_SUCCESS",
            #         'message': "DUMMY_RESPONSE"
            # }
        
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

        except Exception as e:
            error_msg = f"Failed to call vectorial-guard: {str(e)}"
            print(f"[{datetime.now()}] {error_msg}")
            return {
                'service': 'vectorial-guard',
                'success': False,
                'message': error_msg
            }

    def call_both_services_sequential(self, data):
        """Call relational-guard first, then vectorial-guard if successful (sequential pipeline)"""
        print(f"[{datetime.now()}] Starting sequential pipeline...")

        # Call relational service first
        relational_result = self.call_relational_store(data)

        if relational_result['success']:
            print(f"[{datetime.now()}] Relational storage successful, proceeding with vectorial storage...")

            # Call vectorial service with vectorial_data if provided, otherwise use original data
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
        
def shorten(obj, max_str=50, max_list=10):
    if isinstance(obj, str):
        return obj if len(obj) <= max_str else obj[:max_str] + "..."
    elif isinstance(obj, list):
        if len(obj) > max_list:
            return obj[:max_list] + [f"... ({len(obj) - max_list} more items)"]
        return [shorten(x, max_str, max_list) for x in obj]
    elif isinstance(obj, dict):
        return {k: shorten(v, max_str, max_list) for k, v in obj.items()}
    else:
        return obj