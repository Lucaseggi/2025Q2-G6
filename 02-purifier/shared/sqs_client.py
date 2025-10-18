import boto3
import json
import os
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


class SQSClient:
    """AWS SQS client for message queue operations"""

    def __init__(self):
        """Initialize SQS client with LocalStack or AWS configuration"""
        self.sqs = boto3.client(
            'sqs',
            endpoint_url=os.getenv('SQS_ENDPOINT', 'http://localstack:4566'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )

        # Define queue names mapping to URLs
        # Naming convention: scraper(s) -> purifying, purifier(s) -> processing, processor(s) -> embedding, embedder(s) -> inserting
        self.queues = {
            'purifying': os.getenv('PURIFYING_QUEUE_URL'),
            'processing': os.getenv('PROCESSING_QUEUE_URL'),
            'embedding': os.getenv('EMBEDDING_QUEUE_URL'),
            'inserting': os.getenv('INSERTING_QUEUE_URL')
        }

        logger.debug(f"SQS Client initialized with endpoint: {os.getenv('SQS_ENDPOINT', 'http://localstack:4566')}")

    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specified queue

        Args:
            queue_name: Name of the queue (purifying, processing, embedding, inserting)
            message: Message body as dictionary

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            queue_url = self.queues.get(queue_name)
            if not queue_url:
                logger.error(f"Queue URL not found for queue: {queue_name}")
                return False

            message_body = json.dumps(message)

            response = self.sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body
            )

            logger.debug(f"Message sent to {queue_name}: {response['MessageId']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message to {queue_name}: {e}")
            return False

    def receive_message(self, queue_name: str, timeout: int = 20) -> Optional[Dict[str, Any]]:
        """
        Receive message from specified queue with long polling

        Args:
            queue_name: Name of the queue (purifying, processing, embedding, inserting)
            timeout: Wait time in seconds for messages (max 20 for SQS long polling)

        Returns:
            Message body as dictionary, or None if no message received
        """
        try:
            queue_url = self.queues.get(queue_name)
            if not queue_url:
                logger.error(f"Queue URL not found for queue: {queue_name}")
                return None

            # SQS supports long polling up to 20 seconds
            wait_time_seconds = min(timeout, 20)

            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=['All']
            )

            messages = response.get('Messages', [])
            if not messages:
                logger.debug(f"No message received from {queue_name} within {timeout}s")
                return None

            message = messages[0]
            receipt_handle = message['ReceiptHandle']

            # Parse message body
            try:
                body = json.loads(message['Body'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message from {queue_name}: {e}")
                # Delete malformed message
                self.sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                return None

            # Delete message after successful processing
            self.sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )

            logger.debug(f"Message received from {queue_name}")
            return body

        except Exception as e:
            logger.error(f"Failed to receive message from {queue_name}: {e}")
            return None

    def close(self):
        """Close SQS client (no-op for boto3 client)"""
        # boto3 clients don't need explicit closing
        logger.debug("SQS client close called (no-op)")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
