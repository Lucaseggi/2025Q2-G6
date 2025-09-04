import json
import os
import boto3
from opensearchpy import OpenSearch
from datetime import datetime

def create_sqs_client():
    return boto3.client(
        'sqs',
        endpoint_url=os.getenv('SQS_ENDPOINT'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

def create_opensearch_client():
    host = os.getenv('OPENSEARCH_ENDPOINT', 'http://opensearch:9200')
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
                    "id": {"type": "integer"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "category": {"type": "keyword"},
                    "content_length": {"type": "integer"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384
                    },
                    "timestamp": {"type": "date"},
                    "processed_at": {"type": "date"},
                    "embedded_at": {"type": "date"},
                    "inserted_at": {"type": "date"}
                }
            }
        }
        
        client.indices.create(index=index_name, body=mapping)
        print(f"[{datetime.now()}] Inserter: Created index '{index_name}'")

def main():
    print("Inserter MS started - listening for messages...")
    
    sqs = create_sqs_client()
    opensearch = create_opensearch_client()
    inserting_queue_url = os.getenv('INSERTING_QUEUE_URL')
    
    index_name = "documents"
    ensure_index_exists(opensearch, index_name)
    
    while True:
        try:
            # Poll for messages
            response = sqs.receive_message(
                QueueUrl=inserting_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
            
            if 'Messages' in response:
                for message in response['Messages']:
                    print(f"[{datetime.now()}] Inserter: Received message")
                    
                    # Parse message
                    message_body = json.loads(message['Body'])
                    data = message_body['data']
                    
                    # Add insertion timestamp
                    data['inserted_at'] = datetime.now().isoformat()
                    
                    # Insert into OpenSearch
                    doc_id = data['id']
                    response_os = opensearch.index(
                        index=index_name,
                        id=doc_id,
                        body=data
                    )
                    
                    # Delete processed message
                    sqs.delete_message(
                        QueueUrl=inserting_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                    print(f"[{datetime.now()}] Inserter: Inserted document {doc_id} into OpenSearch - Result: {response_os['result']}")
                    
        except Exception as e:
            print(f"[{datetime.now()}] Inserter: Error: {e}")

if __name__ == "__main__":
    main()