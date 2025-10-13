import sys
import os
import time
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import ProcessedData, ProcessingData, ProcessorMetadata
from structured_logger import StructuredLogger, LogStage

from ..interfaces.purifier_interface import PurifierInterface
from ..interfaces.cache_interface import CacheInterface
from ..interfaces.queue_interface import QueueInterface
from .text_processing_service import TextProcessingService
from .llm_service import LLMService

logger = StructuredLogger("purifier", "worker")


class PurifierService(PurifierInterface):
    """Purifier service with text cleaning and LLM orthography fixes"""

    def __init__(
        self,
        cache_service: CacheInterface,
        queue_service: QueueInterface,
        text_processor: TextProcessingService,
        llm_service: LLMService
    ):
        """Initialize purifier service with injected dependencies"""
        self.cache = cache_service
        self.queue = queue_service
        self.text_processor = text_processor
        self.llm_service = llm_service

    def _get_cache_key(self, norm_id: int) -> str:
        """Generate cache key for a norm"""
        return f"purified/{norm_id}.json"

    def process_from_queue(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """Process a message from the scraping queue"""
        start_time = time.time()

        try:
            # Unwrap cached data if needed
            if 'cached_at' in message and 'data' in message:
                actual_data = message['data']
            else:
                actual_data = message

            input_data = ProcessedData.from_dict(actual_data)
            infoleg_id = input_data.scraping_data.infoleg_response.infoleg_id

            logger.log_message_received(
                queue_name='purifying',
                infoleg_id=infoleg_id
            )

            logger.log_processing_start(infoleg_id=infoleg_id)

            # Step 1: Text purification (basic cleaning)
            logger.info(
                "Starting text purification",
                stage=LogStage.PURIFICATION,
                infoleg_id=infoleg_id
            )

            texto_norma = input_data.scraping_data.infoleg_response.texto_norma
            texto_actualizado = input_data.scraping_data.infoleg_response.texto_norma_actualizado

            purified_original, purified_updated = self.text_processor.purify_norm_text(
                texto_norma, texto_actualizado
            )

            # Determine primary text to fix
            primary_text = None
            primary_field = None

            if purified_updated and self.text_processor.is_valid_text(purified_updated):
                primary_text = purified_updated
                primary_field = "updated_text"
            elif purified_original and self.text_processor.is_valid_text(purified_original):
                primary_text = purified_original
                primary_field = "original_text"

            if not primary_text:
                logger.log_processing_failed(
                    infoleg_id=infoleg_id,
                    error="No valid text after purification"
                )
                return False, "no_valid_text"

            logger.info(
                "Text purification complete",
                stage=LogStage.PURIFICATION,
                infoleg_id=infoleg_id,
                primary_field=primary_field,
                original_length=len(texto_norma) if texto_norma else 0,
                purified_length=len(primary_text)
            )

            # Step 2: LLM orthography and numbering fixes
            fix_result = self.llm_service.fix_orthography_and_numbering(primary_text, infoleg_id)

            if not fix_result.success:
                logger.error(
                    "LLM orthography fix failed, continuing with basic purification",
                    stage=LogStage.LLM_CALL,
                    infoleg_id=infoleg_id,
                    error=fix_result.error_message
                )
                # Continue with basic purification even if LLM fails
                fixed_text = primary_text
                model_used = "none"
                tokens_used = 0
            else:
                fixed_text = fix_result.fixed_text
                model_used = fix_result.model_used
                tokens_used = fix_result.tokens_used
                logger.log_llm_call(
                    infoleg_id=infoleg_id,
                    model=model_used,
                    tokens=tokens_used,
                    duration_ms=fix_result.processing_time * 1000 if fix_result.processing_time else None
                )

            # Update the purified texts with fixed version
            if primary_field == "updated_text":
                purified_updated = fixed_text
            else:
                purified_original = fixed_text

            # Step 3: Create processing data with purifications
            processor_metadata = ProcessorMetadata(
                model_used=model_used,
                tokens_used=tokens_used,
                processing_timestamp=datetime.now().isoformat()
            )

            processing_data = ProcessingData(
                purifications={
                    "original_text": purified_original or "",
                    "updated_text": purified_updated or ""
                },
                parsings={},  # Will be filled by processor
                processor_metadata=processor_metadata,
                embedder_metadata=None
            )

            input_data.processing_data = processing_data

            # Step 4: Cache the result
            cache_key = self._get_cache_key(infoleg_id)
            output_data = input_data.to_dict()
            logger.info(
                "Caching purified norm",
                stage=LogStage.CACHE_WRITE,
                infoleg_id=infoleg_id
            )
            self.cache.put(cache_key, output_data)

            # Step 5: Send to purification queue
            success = self.queue.send_message(
                self.llm_service.settings.rabbitmq.queues['output'],
                output_data
            )

            if success:
                duration_ms = (time.time() - start_time) * 1000
                logger.log_message_sent(
                    queue_name='processing',
                    infoleg_id=infoleg_id
                )
                logger.log_processing_complete(
                    infoleg_id=infoleg_id,
                    duration_ms=duration_ms,
                    model_used=model_used,
                    tokens_used=tokens_used
                )
                return True, "purified"
            else:
                logger.error(
                    "Failed to send to processing queue",
                    stage=LogStage.QUEUE_ERROR,
                    infoleg_id=infoleg_id
                )
                return False, "queue_failed"

        except Exception as e:
            logger.log_processing_failed(
                infoleg_id=infoleg_id if 'infoleg_id' in locals() else None,
                error=str(e),
                error_type=type(e).__name__
            )
            return False, f"error: {str(e)}"

    def replay_norm(self, norm_id: int, force: bool = False) -> Tuple[bool, str]:
        """Replay a norm from cache to the purification queue"""
        logger.info(f"Replaying norm {norm_id} (force={force})")

        cache_key = self._get_cache_key(norm_id)

        # Check cache
        cached_data = self.cache.get(cache_key)
        if not cached_data:
            logger.error(f"Norm {norm_id} not found in cache")
            return False, "not_in_cache"

        # Extract the actual data
        if 'data' in cached_data:
            actual_data = cached_data['data']
        else:
            actual_data = cached_data

        # Send to purification queue
        success = self.queue.send_message(
            self.llm_service.settings.rabbitmq.queues['output'],
            actual_data
        )

        if success:
            logger.info(f"Successfully replayed norm {norm_id} to processing queue")
            return True, "replayed"
        else:
            logger.error(f"Failed to replay norm {norm_id}")
            return False, "queue_failed"

    def is_cached(self, norm_id: int) -> bool:
        """Check if a norm is cached"""
        cache_key = self._get_cache_key(norm_id)
        return self.cache.exists(cache_key)
