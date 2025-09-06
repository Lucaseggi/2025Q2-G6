"""Utility functions and classes"""

import logging
import logging.handlers
import redis.asyncio as redis
import json
import time
from pathlib import Path
from typing import Dict, Any

from .config import Config


def setup_logging(config):
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_file = Path(config.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.file,
        maxBytes=_parse_size(config.max_size),
        backupCount=config.backup_count
    )
    file_handler.setLevel(getattr(logging, config.level.upper()))
    file_formatter = logging.Formatter(config.format)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.level.upper()))
    console_formatter = logging.Formatter(config.format)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def _parse_size(size_str: str) -> int:
    """Parse size string like '10MB' to bytes"""
    size_str = size_str.upper()
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


class RedisManager:
    """Manages Redis connections and operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                db=self.config.redis.db,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
            
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}. Continuing without Redis...")
            self.redis_client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def store_processing_metrics(
        self, 
        norm_id: int, 
        model_used: str, 
        processing_time: float, 
        tokens_used: int
    ):
        """Store processing metrics in Redis"""
        if not self.redis_client:
            return
        
        try:
            metrics = {
                'norm_id': norm_id,
                'model_used': model_used,
                'processing_time': processing_time,
                'tokens_used': tokens_used,
                'timestamp': time.time()
            }
            
            # Store individual metric
            await self.redis_client.hset(
                f"metrics:norm:{norm_id}",
                mapping=metrics
            )
            
            # Add to daily stats
            today = time.strftime("%Y-%m-%d")
            await self.redis_client.hincrby(f"daily_stats:{today}", "processed", 1)
            await self.redis_client.hincrby(f"daily_stats:{today}", "tokens_used", tokens_used)
            await self.redis_client.hincrbyfloat(f"daily_stats:{today}", "total_time", processing_time)
            
            # Track model usage
            await self.redis_client.hincrby(f"model_stats:{today}", model_used, 1)
            
        except Exception as e:
            self.logger.warning(f"Failed to store metrics in Redis: {e}")
    
    async def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Get daily processing statistics"""
        if not self.redis_client:
            return {}
        
        if not date:
            date = time.strftime("%Y-%m-%d")
        
        try:
            stats = await self.redis_client.hgetall(f"daily_stats:{date}")
            model_stats = await self.redis_client.hgetall(f"model_stats:{date}")
            
            return {
                'date': date,
                'processed': int(stats.get('processed', 0)),
                'tokens_used': int(stats.get('tokens_used', 0)),
                'total_time': float(stats.get('total_time', 0)),
                'model_usage': {k: int(v) for k, v in model_stats.items()}
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get daily stats from Redis: {e}")
            return {}
    
    async def get_processing_rate(self, hours: int = 1) -> float:
        """Get processing rate (norms per hour) for the last N hours"""
        if not self.redis_client:
            return 0.0
        
        try:
            end_time = time.time()
            start_time = end_time - (hours * 3600)
            
            # This is a simplified version - in practice you might want to store
            # more detailed time-series data
            today = time.strftime("%Y-%m-%d")
            daily_stats = await self.get_daily_stats(today)
            
            if daily_stats.get('total_time', 0) > 0:
                processed = daily_stats.get('processed', 0)
                total_time_hours = daily_stats.get('total_time', 0) / 3600
                return processed / max(total_time_hours, 0.1)  # Avoid division by zero
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate processing rate: {e}")
            return 0.0