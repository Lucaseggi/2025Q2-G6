import boto3
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SQSClient:
    """
    AWS SQS client for message queue operations.

    Configured explicitly by Settings - no environment detection.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        region_name: str = 'us-east-1',
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize SQS client with explicit configuration from Settings.

        Args:
            endpoint_url: SQS endpoint (for LocalStack). None for AWS.
            region_name: AWS region
            aws_access_key_id: AWS access key (for LocalStack). None for Lambda IAM role.
            aws_secret_access_key: AWS secret key (for LocalStack). None for Lambda IAM role.
        """
        # Build client configuration
        client_config = {
            'region_name': region_name
        }

        # Add endpoint if provided (LocalStack)
        if endpoint_url:
            client_config['endpoint_url'] = endpoint_url
            logger.debug(f"SQS Client initialized with endpoint: {endpoint_url}")

        # Add credentials if provided (LocalStack); omit for Lambda IAM role
        if aws_access_key_id and aws_secret_access_key:
            client_config['aws_access_key_id'] = aws_access_key_id
            client_config['aws_secret_access_key'] = aws_secret_access_key
            logger.debug("SQS Client initialized with explicit credentials (LocalStack)")
        else:
            logger.debug("SQS Client initialized for Lambda (using IAM role)")

        self.sqs = boto3.client('sqs', **client_config)

        # Cache for queue URLs resolved from queue names
        self._queue_url_cache = {}

    def _get_queue_url(self, queue_name: str) -> Optional[str]:
        """
        Get queue URL from queue name using AWS SQS API.
        Caches results to avoid repeated API calls.
        """
        if queue_name in self._queue_url_cache:
            return self._queue_url_cache[queue_name]

        try:
            response = self.sqs.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            self._queue_url_cache[queue_name] = queue_url
            logger.debug(f"Resolved queue '{queue_name}' to URL: {queue_url}")
            return queue_url
        except Exception as e:
            logger.error(f"Failed to get queue URL for '{queue_name}': {e}")
            return None

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
            queue_url = self._get_queue_url(queue_name)
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
            queue_url = self._get_queue_url(queue_name)
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
