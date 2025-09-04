import json
import os
import boto3
import hashlib
from datetime import datetime

def create_sqs_client():
    return boto3.client(
        'sqs',
        endpoint_url=os.getenv('SQS_ENDPOINT'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

def generate_dummy_embedding(text):
    """Generate a dummy embedding vector from text hash"""
    hash_obj = hashlib.md5(text.encode())
    hash_bytes = hash_obj.digest()
    
    # Convert to a 384-dimension vector (typical for sentence transformers)
    embedding = []
    for i in range(0, len(hash_bytes), 1):
        byte_val = hash_bytes[i % len(hash_bytes)]
        # Normalize to [-1, 1] range
        embedding.extend([
            (byte_val & 0x0F) / 15.0 - 0.5,
            ((byte_val & 0xF0) >> 4) / 15.0 - 0.5
        ])
    
    # Pad or truncate to exactly 384 dimensions
    while len(embedding) < 384:
        embedding.extend(embedding[:min(len(embedding), 384 - len(embedding))])
    
    return embedding[:384]

def main():
    print("Embedding MS started - listening for messages...")
    
    sqs = create_sqs_client()
    embedding_queue_url = os.getenv('EMBEDDING_QUEUE_URL')
    inserting_queue_url = os.getenv('INSERTING_QUEUE_URL')
    
    while True:
        try:
            # Poll for messages
            response = sqs.receive_message(
                QueueUrl=embedding_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
            
            if 'Messages' in response:
                for message in response['Messages']:
                    print(f"[{datetime.now()}] Embedding: Received message")
                    
                    # Parse message
                    message_body = json.loads(message['Body'])
                    data = message_body['data']
                    
                    # Generate embedding for content field
                    content_text = data['content']
                    embedding_vector = generate_dummy_embedding(content_text)
                    
                    # Prepare data with embedding
                    embedded_data = data.copy()
                    embedded_data['embedding'] = embedding_vector
                    embedded_data['embedding_model'] = 'dummy-hash-model'
                    embedded_data['embedded_at'] = datetime.now().isoformat()
                    
                    # Send to inserting queue
                    insert_message = {
                        "source": "embedding",
                        "data": embedded_data,
                        "insert_timestamp": datetime.now().isoformat()
                    }
                    
                    sqs.send_message(
                        QueueUrl=inserting_queue_url,
                        MessageBody=json.dumps(insert_message)
                    )
                    
                    # Delete processed message
                    sqs.delete_message(
                        QueueUrl=embedding_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                    print(f"[{datetime.now()}] Embedding: Generated embedding for document {data['id']} and sent to inserting queue")
                    
        except Exception as e:
            print(f"[{datetime.now()}] Embedding: Error: {e}")

if __name__ == "__main__":
    main()