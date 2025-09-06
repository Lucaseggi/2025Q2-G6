"""Configuration management"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path


@dataclass
class DatabaseConfig:
    dbname: str
    user: str
    password: str
    host: str
    port: int


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int


@dataclass
class GeminiConfig:
    models: List[str]
    api_keys: List[str]
    rate_limit: int
    max_input_tokens: int
    max_output_tokens: int
    max_retries: int
    retry_delay: int
    diff_threshold: float


@dataclass
class ProcessingConfig:
    batch_size: int
    max_concurrent_requests: int
    progress_report_interval: int
    checkpoint_interval: int
    max_text_length: int
    min_text_length: int


@dataclass
class EmailConfig:
    enabled: bool
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    recipient_email: str = ""
    daily_report: bool = True
    error_notifications: bool = True


@dataclass
class LoggingConfig:
    level: str
    file: str
    max_size: str
    backup_count: int
    format: str


@dataclass
class ErrorHandlingConfig:
    max_consecutive_failures: int
    failure_cooldown: int
    max_item_retries: int


@dataclass
class Config:
    databases: Dict[str, DatabaseConfig]
    redis: RedisConfig
    gemini: GeminiConfig
    processing: ProcessingConfig
    email: EmailConfig
    logging: LoggingConfig
    error_handling: ErrorHandlingConfig

    @classmethod
    def load(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Expand environment variables
        data = cls._expand_env_vars(data)
        
        return cls(
            databases={
                name: DatabaseConfig(**db_config)
                for name, db_config in data['databases'].items()
            },
            redis=RedisConfig(**data['redis']),
            gemini=GeminiConfig(**data['gemini']),
            processing=ProcessingConfig(**data['processing']),
            email=EmailConfig(**data.get('email', {'enabled': False})),
            logging=LoggingConfig(**data['logging']),
            error_handling=ErrorHandlingConfig(**data['error_handling'])
        )
    
    @staticmethod
    def _expand_env_vars(data: Any) -> Any:
        """Recursively expand environment variables in configuration"""
        if isinstance(data, dict):
            return {k: Config._expand_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Config._expand_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith('${') and data.endswith('}'):
            env_var = data[2:-1]
            env_value = os.getenv(env_var)
            if env_value is None:
                raise ValueError(f"Required environment variable '{env_var}' is not set")
            return env_value
        return data