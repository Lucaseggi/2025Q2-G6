"""Configuration settings for the embedding service"""

import json
import os
from functools import lru_cache
from pydantic import BaseModel

CONFIG_FILE = "config.json"


class ServiceConfig(BaseModel):
    name: str
    version: str
    port: int
    debug: bool


class RabbitMQQueues(BaseModel):
    input: str
    output: str


class RabbitMQConfig(BaseModel):
    host: str
    port: int
    user: str
    vhost: str
    queues: RabbitMQQueues


class EmbeddingConfig(BaseModel):
    embedding_model_name: str
    output_dimensionality: int
    provider: str
    max_retries: int = 5


class Settings(BaseModel):
    service: ServiceConfig
    rabbitmq: RabbitMQConfig
    embedding: EmbeddingConfig


def load_config() -> Settings:
    """Load configuration from config.json file"""
    # Try multiple possible locations for config.json
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), CONFIG_FILE),  # /app/config.json
        os.path.join(os.getcwd(), CONFIG_FILE),  # Current working directory
        CONFIG_FILE  # Relative to current directory
    ]

    config_path = None
    for path in possible_paths:
        if os.path.exists(path):
            config_path = path
            break

    if not config_path:
        raise FileNotFoundError(f"Could not find {CONFIG_FILE} in any of: {possible_paths}")

    with open(config_path, 'r') as f:
        config_data = json.load(f)

    return Settings(**config_data)


@lru_cache()
def get_settings() -> Settings:
    """Get cached configuration settings"""
    return load_config()