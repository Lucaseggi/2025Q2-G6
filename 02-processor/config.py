"""Configuration management for processor service using JSON + environment variables"""

import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class ServiceConfig:
    """Service configuration"""
    name: str
    version: str
    debug: bool


@dataclass
class RabbitMQConfig:
    """RabbitMQ configuration"""
    host: str
    port: int
    user: str
    password: str  # From environment
    vhost: str
    queues: Dict[str, str]


@dataclass
class GeminiConfig:
    """Gemini LLM configuration"""
    models: List[str]
    api_keys: List[str]  # From environment
    rate_limit: int
    max_input_tokens: int
    max_output_tokens: int
    max_retries: int
    retry_delay: int
    diff_threshold: float




@dataclass
class S3Config:
    """S3 configuration"""
    endpoint: str
    bucket_name: str
    access_key_id: str
    secret_access_key: str
    region: str


@dataclass
class ProcessingConfig:
    """Processing configuration"""
    batch_size: int
    timeout_seconds: int
    stats_interval_minutes: int


class ProcessorSettings:
    """Main processor settings combining JSON config and environment variables"""

    def __init__(self, config_path: str = "config.json"):
        """Initialize settings from JSON config and environment variables"""
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        """Load configuration from JSON file and environment variables"""
        # Load JSON configuration
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")

        with open(config_file, 'r') as f:
            config_data = json.load(f)

        # Initialize service config
        service_data = config_data["service"]
        self.service = ServiceConfig(
            name=service_data["name"],
            version=service_data["version"],
            debug=service_data.get("debug", False)
        )

        # Initialize RabbitMQ config (password from environment)
        rabbitmq_data = config_data["rabbitmq"]
        self.rabbitmq = RabbitMQConfig(
            host=rabbitmq_data["host"],
            port=rabbitmq_data["port"],
            user=rabbitmq_data["user"],
            password=os.getenv("RABBITMQ_PASSWORD", "admin123"),
            vhost=rabbitmq_data["vhost"],
            queues=rabbitmq_data["queues"]
        )

        # Initialize S3 config
        s3_data = config_data["s3"]
        self.s3 = S3Config(
            endpoint=s3_data["endpoint"],
            bucket_name=s3_data["bucket_name"],
            access_key_id=s3_data["access_key_id"],
            secret_access_key=s3_data["secret_access_key"],
            region=s3_data["region"]
        )

        # Initialize Gemini config (API keys from environment)
        gemini_data = config_data["gemini"]
        self.gemini = GeminiConfig(
            models=gemini_data["models"],
            api_keys=self._get_api_keys(),
            rate_limit=gemini_data["rate_limit"],
            max_input_tokens=gemini_data["max_input_tokens"],
            max_output_tokens=gemini_data["max_output_tokens"],
            max_retries=gemini_data["max_retries"],
            retry_delay=gemini_data["retry_delay"],
            diff_threshold=gemini_data["diff_threshold"]
        )


        # Initialize processing config
        processing_data = config_data["processing"]
        self.processing = ProcessingConfig(
            batch_size=processing_data["batch_size"],
            timeout_seconds=processing_data["timeout_seconds"],
            stats_interval_minutes=processing_data["stats_interval_minutes"]
        )

    def _get_api_keys(self) -> List[str]:
        """Get API keys from environment variables"""
        keys = []

        # Check for multiple API keys
        for i in range(1, 6):  # Check for up to 5 API keys
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                keys.append(key)

        # Fallback to single API key
        if not keys:
            key = os.getenv('GEMINI_API_KEY')
            if key:
                keys.append(key)

        if not keys:
            raise ValueError("No Gemini API keys found in environment variables")

        return keys


    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        # Environment variable can override JSON setting
        debug_env = os.getenv('DEBUG', '').lower()
        if debug_env in ['1', 'true', 'yes']:
            return True
        elif debug_env in ['0', 'false', 'no']:
            return False
        return self.service.debug


