"""
Structured Logger for Simpla Data Extraction Pipeline

Provides standardized logging across all microservices with:
- JSON formatting for sidecar parsing
- Consistent field names and structure
- Stage-based logging
- Correlation IDs for tracing
- Human-readable console output
"""

import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class LogStage(str, Enum):
    """Standard logging stages across all microservices"""
    # Common stages
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    HEALTH_CHECK = "health_check"

    # Queue/Message stages
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    QUEUE_ERROR = "queue_error"

    # Processing stages
    PROCESSING_START = "processing_start"
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_FAILED = "processing_failed"

    # Cache stages
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_WRITE = "cache_write"
    CACHE_ERROR = "cache_error"

    # API stages
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_ERROR = "api_error"

    # Service-specific stages
    SCRAPING = "scraping"
    PURIFICATION = "purification"
    LLM_CALL = "llm_call"
    VERIFICATION = "verification"
    EMBEDDING = "embedding"
    INSERTION = "insertion"

    # Storage stages
    STORAGE_WRITE = "storage_write"
    STORAGE_READ = "storage_read"
    STORAGE_ERROR = "storage_error"


class StructuredLogger:
    """Structured logger that outputs JSON for sidecar parsing and human-readable console logs"""

    def __init__(self, service_name: str, service_type: str = "service"):
        """
        Initialize structured logger

        Args:
            service_name: Name of the microservice (e.g., 'scraper', 'purifier')
            service_type: Type of service (e.g., 'api', 'worker')
        """
        self.service_name = service_name
        self.service_type = service_type

        # Setup log directory and file
        log_file = os.getenv('LOG_FILE', '/app/logs/app.log')
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(f"{service_name}-{service_type}")
        self.logger.setLevel(logging.DEBUG if os.getenv('DEBUG', 'false').lower() == 'true' else logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler for structured JSON logs (for sidecar consumption)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(message)s'))

        # Console handler for human-readable logs (for docker logs command)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _log(
        self,
        level: str,
        message: str,
        stage: Optional[LogStage] = None,
        infoleg_id: Optional[int] = None,
        **kwargs
    ):
        """
        Internal logging method that creates structured log entries

        Args:
            level: Log level (INFO, ERROR, WARNING, DEBUG)
            message: Human-readable message
            stage: Processing stage
            infoleg_id: Document ID for correlation
            **kwargs: Additional contextual data
        """
        # Build structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "service_type": self.service_type,
            "level": level,
            "stage": stage.value if stage else None,
            "message": message,
        }

        # Add infoleg_id if provided (for correlation)
        if infoleg_id is not None:
            log_entry["infoleg_id"] = infoleg_id

        # Add all additional context
        log_entry.update(kwargs)

        # Write JSON to file handler (for sidecar)
        if self.logger.handlers:
            file_handler = self.logger.handlers[0]
            record = logging.LogRecord(
                name=self.logger.name,
                level=getattr(logging, level),
                pathname="",
                lineno=0,
                msg=json.dumps(log_entry, default=str),
                args=(),
                exc_info=None
            )
            file_handler.emit(record)

            # Write human-readable to console handler
            if len(self.logger.handlers) > 1:
                console_handler = self.logger.handlers[1]
                console_msg = message
                if infoleg_id:
                    console_msg = f"[ID:{infoleg_id}] {console_msg}"
                if stage:
                    console_msg = f"[{stage.value}] {console_msg}"

                console_record = logging.LogRecord(
                    name=self.logger.name,
                    level=getattr(logging, level),
                    pathname="",
                    lineno=0,
                    msg=console_msg,
                    args=(),
                    exc_info=None
                )
                console_handler.emit(console_record)

    # Standard log methods
    def info(self, message: str, stage: Optional[LogStage] = None, infoleg_id: Optional[int] = None, **kwargs):
        """Log info level message"""
        self._log("INFO", message, stage=stage, infoleg_id=infoleg_id, **kwargs)

    def error(self, message: str, stage: Optional[LogStage] = None, infoleg_id: Optional[int] = None, **kwargs):
        """Log error level message"""
        self._log("ERROR", message, stage=stage, infoleg_id=infoleg_id, **kwargs)

    def warning(self, message: str, stage: Optional[LogStage] = None, infoleg_id: Optional[int] = None, **kwargs):
        """Log warning level message"""
        self._log("WARNING", message, stage=stage, infoleg_id=infoleg_id, **kwargs)

    def debug(self, message: str, stage: Optional[LogStage] = None, infoleg_id: Optional[int] = None, **kwargs):
        """Log debug level message"""
        self._log("DEBUG", message, stage=stage, infoleg_id=infoleg_id, **kwargs)

    # Convenience methods for common patterns
    def log_message_received(self, queue_name: str, infoleg_id: Optional[int] = None, **kwargs):
        """Log when a message is received from a queue"""
        self.info(
            f"Message received from queue: {queue_name}",
            stage=LogStage.MESSAGE_RECEIVED,
            infoleg_id=infoleg_id,
            queue=queue_name,
            **kwargs
        )

    def log_message_sent(self, queue_name: str, infoleg_id: Optional[int] = None, **kwargs):
        """Log when a message is sent to a queue"""
        self.info(
            f"Message sent to queue: {queue_name}",
            stage=LogStage.MESSAGE_SENT,
            infoleg_id=infoleg_id,
            queue=queue_name,
            **kwargs
        )

    def log_processing_start(self, infoleg_id: int, **kwargs):
        """Log start of document processing"""
        self.info(
            f"Starting processing",
            stage=LogStage.PROCESSING_START,
            infoleg_id=infoleg_id,
            **kwargs
        )

    def log_processing_complete(self, infoleg_id: int, duration_ms: Optional[float] = None, **kwargs):
        """Log successful completion of processing"""
        msg = f"Processing complete"
        if duration_ms:
            msg += f" ({duration_ms:.0f}ms)"

        self.info(
            msg,
            stage=LogStage.PROCESSING_COMPLETE,
            infoleg_id=infoleg_id,
            duration_ms=duration_ms,
            **kwargs
        )

    def log_processing_failed(self, infoleg_id: int, error: str, **kwargs):
        """Log failed processing"""
        self.error(
            f"Processing failed: {error}",
            stage=LogStage.PROCESSING_FAILED,
            infoleg_id=infoleg_id,
            error=error,
            **kwargs
        )

    def log_cache_hit(self, infoleg_id: int, **kwargs):
        """Log cache hit"""
        self.info(
            "Cache hit",
            stage=LogStage.CACHE_HIT,
            infoleg_id=infoleg_id,
            **kwargs
        )

    def log_cache_miss(self, infoleg_id: int, **kwargs):
        """Log cache miss"""
        self.info(
            "Cache miss",
            stage=LogStage.CACHE_MISS,
            infoleg_id=infoleg_id,
            **kwargs
        )

    def log_llm_call(self, infoleg_id: int, model: str, tokens: Optional[int] = None, duration_ms: Optional[float] = None, **kwargs):
        """Log LLM API call"""
        msg = f"LLM call to {model}"
        if tokens:
            msg += f" ({tokens} tokens)"

        self.info(
            msg,
            stage=LogStage.LLM_CALL,
            infoleg_id=infoleg_id,
            model=model,
            tokens=tokens,
            duration_ms=duration_ms,
            **kwargs
        )

    def log_api_request(self, endpoint: str, method: str = "GET", **kwargs):
        """Log API request"""
        self.info(
            f"{method} {endpoint}",
            stage=LogStage.API_REQUEST,
            endpoint=endpoint,
            method=method,
            **kwargs
        )

    def log_api_response(self, endpoint: str, status_code: int, duration_ms: Optional[float] = None, **kwargs):
        """Log API response"""
        self.info(
            f"Response {status_code} for {endpoint}",
            stage=LogStage.API_RESPONSE,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )

    def log_statistics(self, stats: Dict[str, Any]):
        """Log processing statistics"""
        self.info(
            "Processing statistics",
            stage=LogStage.PROCESSING_COMPLETE,
            **stats
        )
