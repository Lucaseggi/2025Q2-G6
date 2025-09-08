import json
import os
import sys
from opensearchpy import OpenSearch
from datetime import datetime

sys.path.append('/app/00-shared')
from rabbitmq_client import RabbitMQClient

def create_queue_client():
    return RabbitMQClient()

def create_opensearch_client():
    host = os.getenv('OPENSEARCH_ENDPOINT')
    client = OpenSearch(
        hosts=[host],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    return client

def ensure_index_exists(client, index_name):
    """Create index if it doesn't exist"""
    if not client.indices.exists(index=index_name):
        mapping = {
            "mappings": {
                "properties": {
                    "norma": {
                        "properties": {
                            "infoleg_id": {"type": "integer"},
                            "jurisdiccion": {"type": "keyword"},
                            "clase_norma": {"type": "keyword"},
                            "tipo_norma": {"type": "keyword"},
                            "sancion": {"type": "date"},
                            "publicacion": {"type": "date"},
                            "titulo_sumario": {"type": "text"},
                            "titulo_resumido": {"type": "text"},
                            "observaciones": {"type": "text"},
                            "nro_boletin": {"type": "keyword"},
                            "pag_boletin": {"type": "keyword"},
                            "estado": {"type": "keyword"},
                            "purified_texto_norma": {"type": "text"},
                            "purified_texto_norma_actualizado": {"type": "text"},
                            "structured_texto_norma": {"type": "object"},
                            "structured_texto_norma_actualizado": {"type": "object"}
                        }
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 768,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "embedding_model": {"type": "keyword"},
                    "embedding_source": {"type": "keyword"},
                    "embedded_at": {"type": "date"},
                    "inserted_at": {"type": "date"}
                }
            }
        }
        
        client.indices.create(index=index_name, body=mapping)
        print(f"[{datetime.now()}] Inserter: Created index '{index_name}'")

def main():
    print("Inserter MS started - listening for messages...")
    
    queue_client = create_queue_client()
    opensearch = create_opensearch_client()
    
    index_name = "documents"
    ensure_index_exists(opensearch, index_name)
    
    while True:
        try:
            # Receive message from inserting queue
            message_body = queue_client.receive_message('inserting', timeout=20)
            
            if message_body:
                print(f"[{datetime.now()}] Inserter: Received message")
                
                # DEBUG: Print the complete dequeued message for analysis
                print("="*100)
                print("COMPLETE DEQUEUED MESSAGE FROM EMBEDDING-MS:")
                print("="*100)
                print(json.dumps(message_body, indent=2, default=str))
                print("="*100)
                
                data = message_body['data']
                
                # Add insertion timestamp
                data['inserted_at'] = datetime.now().isoformat()
                
                # Get document ID from norma
                doc_id = data['norma']['infoleg_id']
                
                # DEBUG: Print the final document structure before insertion
                print("-"*100)
                print(f"FINAL DOCUMENT STRUCTURE FOR OPENSEARCH (ID: {doc_id}):")
                print("-"*100)
                print(f"Document ID: {doc_id}")
                print(f"Embedding dimensions: {len(data.get('embedding', []))}")
                print(f"Embedding model: {data.get('embedding_model', 'N/A')}")
                print(f"Embedding source: {data.get('embedding_source', 'N/A')}")
                print(f"Norma keys: {list(data['norma'].keys()) if 'norma' in data else 'N/A'}")
                print(f"Has purified_texto_norma: {'purified_texto_norma' in data['norma'] and bool(data['norma']['purified_texto_norma'])}")
                print(f"Has purified_texto_norma_actualizado: {'purified_texto_norma_actualizado' in data['norma'] and bool(data['norma']['purified_texto_norma_actualizado'])}")
                print(f"Has structured_texto_norma: {'structured_texto_norma' in data['norma'] and bool(data['norma']['structured_texto_norma'])}")
                print(f"Has structured_texto_norma_actualizado: {'structured_texto_norma_actualizado' in data['norma'] and bool(data['norma']['structured_texto_norma_actualizado'])}")
                print("-"*100)
                
                # Insert into OpenSearch
                response_os = opensearch.index(
                    index=index_name,
                    id=doc_id,
                    body=data
                )
                
                # Message acknowledged automatically by RabbitMQ
                
                print(f"[{datetime.now()}] Inserter: Inserted document {doc_id} into OpenSearch - Result: {response_os['result']}")
                print(f"[{datetime.now()}] Inserter: OpenSearch response: {response_os}")
                    
        except Exception as e:
            print(f"[{datetime.now()}] Inserter: Error: {e}")

if __name__ == "__main__":
    main()