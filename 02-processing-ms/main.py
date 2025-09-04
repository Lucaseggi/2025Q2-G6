import json
import os
import boto3
from datetime import datetime

def create_sqs_client():
    return boto3.client(
        'sqs',
        endpoint_url=os.getenv('SQS_ENDPOINT'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

def process_data(raw_data):
    """Simulate data processing and cleaning"""
    processed_data = raw_data.copy()
    
    # Clean and enhance data
    processed_data['title'] = processed_data['title'].strip().upper()
    processed_data['content_length'] = len(processed_data['content'])
    processed_data['processed_at'] = datetime.now().isoformat()
    processed_data['status'] = 'processed'
    
    return processed_data

def main():
    print("Processing MS started - listening for messages...")
    
    sqs = create_sqs_client()
    processing_queue_url = os.getenv('PROCESSING_QUEUE_URL')
    embedding_queue_url = os.getenv('EMBEDDING_QUEUE_URL')
    
    while True:
        try:
            # Poll for messages
            response = sqs.receive_message(
                QueueUrl=processing_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20  # Long polling
            )
            
            if 'Messages' in response:
                for message in response['Messages']:
                    print(f"[{datetime.now()}] Processing: Received message")
                    
                    # Parse message
                    message_body = json.loads(message['Body'])
                    raw_data = message_body['data']
                    
                    # Process the data
                    processed_data = process_data(raw_data)
                    
                    # Send to embedding queue
                    processed_message = {
                        "source": "processing",
                        "data": processed_data,
                        "embedding_timestamp": datetime.now().isoformat()
                    }
                    
                    sqs.send_message(
                        QueueUrl=embedding_queue_url,
                        MessageBody=json.dumps(processed_message)
                    )
                    
                    # Delete processed message
                    sqs.delete_message(
                        QueueUrl=processing_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                    print(f"[{datetime.now()}] Processing: Processed document {processed_data['id']} and sent to embedding queue")
                    
        except Exception as e:
            print(f"[{datetime.now()}] Processing: Error: {e}")

if __name__ == "__main__":
    main()