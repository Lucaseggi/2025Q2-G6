import boto3
import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QueueClient:
    def __init__(self):
        self.sqs = boto3.client(
            'sqs',
            endpoint_url=os.getenv('SQS_ENDPOINT', 'http://localhost:4566'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
        
        self.queues = {
            'processing': os.getenv('PROCESSING_QUEUE_URL'),
            'embedding': os.getenv('EMBEDDING_QUEUE_URL'),
            'inserting': os.getenv('INSERTING_QUEUE_URL')
        }
        
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        try:
            queue_url = self.queues.get(queue_name)
            if not queue_url:
                logger.error(f"Queue URL not found for queue: {queue_name}")
                return False
                
            response = self.sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            logger.info(f"Message sent to {queue_name}: {response['MessageId']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {queue_name}: {str(e)}")
            return False
            
    def receive_message(self, queue_name: str, wait_time: int = 20) -> Optional[Dict[str, Any]]:
        try:
            queue_url = self.queues.get(queue_name)
            if not queue_url:
                logger.error(f"Queue URL not found for queue: {queue_name}")
                return None
                
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_time
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return None
                
            message = messages[0]
            receipt_handle = message['ReceiptHandle']
            body = json.loads(message['Body'])
            
            self.sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            
            return body
        except Exception as e:
            logger.error(f"Failed to receive message from {queue_name}: {str(e)}")
            return None