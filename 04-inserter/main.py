import json
import os
import sys
import requests
from datetime import datetime

sys.path.append('/app/00-shared')
from rabbitmq_client import RabbitMQClient

def create_queue_client():
    return RabbitMQClient()

def send_to_django_api(data):
    """Send data to Django API for dual database insertion"""
    django_api_url = os.getenv('DJANGO_API_URL', 'http://api:8000')
    endpoint = f"{django_api_url}/api/data/ingest/"

    try:
        response = requests.post(
            endpoint,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print(f"[{datetime.now()}] Inserter: Django API success: {result.get('success')}")
            return result
        else:
            print(f"[{datetime.now()}] Inserter: Django API error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"[{datetime.now()}] Inserter: Django API request failed: {e}")
        return None

def main():
    print("Inserter MS started - listening for messages...")
    print(f"Django API URL: {os.getenv('DJANGO_API_URL', 'http://api:8000')}")

    queue_client = create_queue_client()
    
    while True:
        try:
            # Receive message from inserting queue
            message_body = queue_client.receive_message('inserting', timeout=20)
            
            if message_body:
                print(f"[{datetime.now()}] Inserter: Received message")
                
                # DEBUG: Print the complete dequeued message for analysis (with embedding truncated)
                print("="*100)
                print("COMPLETE DEQUEUED MESSAGE FROM EMBEDDING-MS:")
                print("="*100)

                # Create a copy for logging with embedding truncated
                log_message = json.loads(json.dumps(message_body, default=str))
                if 'data' in log_message and 'embedding' in log_message['data']:
                    embedding_length = len(log_message['data']['embedding'])
                    log_message['data']['embedding'] = f"[EMBEDDING_VECTOR_{embedding_length}_DIMS]"

                # Also truncate embeddings in structured data if present
                def truncate_embeddings_in_dict(obj):
                    if isinstance(obj, dict):
                        result = {}
                        for key, value in obj.items():
                            if key == 'embedding' and isinstance(value, list):
                                result[key] = f"[EMBEDDING_VECTOR_{len(value)}_DIMS]"
                            else:
                                result[key] = truncate_embeddings_in_dict(value)
                        return result
                    elif isinstance(obj, list):
                        return [truncate_embeddings_in_dict(item) for item in obj]
                    else:
                        return obj

                log_message = truncate_embeddings_in_dict(log_message)

                print(json.dumps(log_message, indent=2, default=str))
                print("="*100)
                
                # Add insertion timestamp to the message
                message_body['insert_timestamp'] = datetime.now().isoformat()

                # Get document ID for logging
                doc_id = message_body['data']['norma']['infoleg_id']

                # DEBUG: Print summary before sending to Django
                print("-"*100)
                print(f"SENDING TO DJANGO API (Norma ID: {doc_id}):")
                print("-"*100)
                data = message_body['data']
                print(f"Embedding type: {data.get('embedding_type', 'N/A')}")
                print(f"Embedding dimensions: {len(data.get('embedding', []))}")
                print(f"Has structured data: {bool(data['norma'].get('structured_texto_norma') or data['norma'].get('structured_texto_norma_actualizado'))}")

                if data['norma'].get('structured_texto_norma_actualizado'):
                    structured = data['norma']['structured_texto_norma_actualizado']
                    print(f"Structured divisions: {len(structured.get('divisions', []))}")
                elif data['norma'].get('structured_texto_norma'):
                    structured = data['norma']['structured_texto_norma']
                    print(f"Structured divisions: {len(structured.get('divisions', []))}")

                print("-"*100)

                # Send to Django API for dual database insertion
                api_result = send_to_django_api(message_body)

                if api_result and api_result.get('success'):
                    postgres_status = api_result.get('postgres', {}).get('status', 'unknown')
                    opensearch_status = api_result.get('opensearch', {}).get('status', 'unknown')

                    print(f"[{datetime.now()}] Inserter: Document {doc_id} processed successfully")
                    print(f"[{datetime.now()}] Inserter: PostgreSQL: {postgres_status}")
                    print(f"[{datetime.now()}] Inserter: OpenSearch: {opensearch_status}")
                else:
                    print(f"[{datetime.now()}] Inserter: Failed to process document {doc_id}")
                    if api_result:
                        print(f"[{datetime.now()}] Inserter: Error: {api_result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            print(f"[{datetime.now()}] Inserter: Error: {e}")

if __name__ == "__main__":
    main()