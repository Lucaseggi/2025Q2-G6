import pika
import json
import os
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()
        
        # Define queue names
        self.queues = {
            'processing': 'processing-queue',
            'embedding': 'embedding-queue', 
            'inserting': 'inserting-queue'
        }
        
        # Declare all queues
        self._declare_queues()
        
    def connect(self):
        """Establish connection to RabbitMQ server"""
        try:
            host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
            port = int(os.getenv('RABBITMQ_PORT', '5672'))
            username = os.getenv('RABBITMQ_USER', 'admin') 
            password = os.getenv('RABBITMQ_PASSWORD', 'admin123')
            vhost = os.getenv('RABBITMQ_VHOST', '/')
            
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info(f"Connected to RabbitMQ at {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def _declare_queues(self):
        """Declare all queues to ensure they exist"""
        try:
            for queue_name in self.queues.values():
                self.channel.queue_declare(queue=queue_name, durable=True)
                logger.info(f"Declared queue: {queue_name}")
        except Exception as e:
            logger.error(f"Failed to declare queues: {e}")
            raise
    
    def _ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            if self.connection is None or self.connection.is_closed:
                logger.warning("Connection lost, reconnecting...")
                self.connect()
            elif self.channel is None or self.channel.is_closed:
                logger.warning("Channel lost, recreating...")
                self.channel = self.connection.channel()
                self._declare_queues()
        except Exception as e:
            logger.error(f"Failed to ensure connection: {e}")
            self.connect()
    
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Send message to specified queue"""
        try:
            self._ensure_connection()
            
            queue = self.queues.get(queue_name)
            if not queue:
                logger.error(f"Unknown queue: {queue_name}")
                return False
            
            message_body = json.dumps(message)
            
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            
            logger.info(f"Message sent to {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {queue_name}: {e}")
            return False
    
    def receive_message(self, queue_name: str, timeout: int = 20) -> Optional[Dict[str, Any]]:
        """Receive message from specified queue with timeout"""
        try:
            self._ensure_connection()
            
            queue = self.queues.get(queue_name)
            if not queue:
                logger.error(f"Unknown queue: {queue_name}")
                return None
            
            # Set up timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                method_frame, header_frame, body = self.channel.basic_get(queue=queue)
                
                if method_frame:
                    # Message received
                    try:
                        message = json.loads(body.decode('utf-8'))
                        # Acknowledge message
                        self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                        logger.info(f"Message received from {queue_name}")
                        return message
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message from {queue_name}: {e}")
                        # Reject malformed message
                        self.channel.basic_nack(
                            delivery_tag=method_frame.delivery_tag, 
                            requeue=False
                        )
                        continue
                
                # No message available, wait a bit before retrying
                time.sleep(1)
            
            # Timeout reached
            logger.debug(f"No message received from {queue_name} within {timeout}s")
            return None
            
        except Exception as e:
            logger.error(f"Failed to receive message from {queue_name}: {e}")
            return None
    
    def close(self):
        """Close connection"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()