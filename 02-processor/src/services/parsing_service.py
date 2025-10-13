"""Parsing service implementation that orchestrates text processing, LLM, and verification"""

import json
import time
from datetime import datetime
from typing import Optional
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from models import ProcessedData, ProcessingData, ProcessorMetadata, ParsedText
from structured_logger import StructuredLogger, LogStage

# Add src to path for interfaces
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from interfaces.parsing_service_interface import ParsingServiceInterface
from interfaces.text_processing_interface import TextProcessingInterface
from interfaces.llm_service_interface import LLMServiceInterface
from interfaces.verification_service_interface import VerificationServiceInterface
from interfaces.storage_interface import StorageInterface

logger = StructuredLogger("processor", "worker")


class ParsingService(ParsingServiceInterface):
    """Main parsing service that orchestrates the complete processing pipeline"""

    def __init__(
        self,
        text_processor: TextProcessingInterface,
        llm_service: LLMServiceInterface,
        verification_service: VerificationServiceInterface,
        storage_service: StorageInterface
    ):
        """Initialize parsing service with dependencies"""
        self.text_processor = text_processor
        self.llm_service = llm_service
        self.verification_service = verification_service
        self.storage_service = storage_service

        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed_purification': 0,
            'failed_llm_processing': 0,
            'failed_verification': 0,
            'stored_to_s3': 0,
        }

    def process_document(self, input_data: ProcessedData) -> Optional[ProcessedData]:
        """Process a document through the complete parsing pipeline"""
        start_time = time.time()

        try:
            # Get InfolegApiResponse from scraping data
            infoleg_response = input_data.scraping_data.infoleg_response
            self.stats['total_processed'] += 1

            logger.log_processing_start(infoleg_id=infoleg_response.infoleg_id)

            # Step 1: Get purified text from processing_data (already done by purifier)
            if not input_data.processing_data or not input_data.processing_data.purifications:
                logger.log_processing_failed(
                    infoleg_id=infoleg_response.infoleg_id,
                    error="No purifications found"
                )
                self.stats['failed_purification'] += 1
                return None

            purifications = input_data.processing_data.purifications
            purified_original = purifications.get("original_text", "")
            purified_updated = purifications.get("updated_text", "")

            # Determine primary text to process
            primary_field = None
            primary_purified_text = None

            if purified_updated and self.text_processor.is_valid_text(purified_updated):
                primary_field = "updated_text"
                primary_purified_text = purified_updated
            elif purified_original and self.text_processor.is_valid_text(purified_original):
                primary_field = "original_text"
                primary_purified_text = purified_original

            # Check if we have any content to process
            if not primary_purified_text:
                logger.log_processing_failed(
                    infoleg_id=infoleg_response.infoleg_id,
                    error="No valid purified text"
                )
                self.stats['failed_purification'] += 1
                return None

            # Step 2: LLM processing for structuring
            logger.info(
                f"Starting LLM structuring for {primary_field}",
                stage=LogStage.LLM_CALL,
                infoleg_id=infoleg_response.infoleg_id,
                primary_field=primary_field,
                text_length=len(primary_purified_text)
            )

            # Pass context with infoleg_id for better logging
            context = {"infoleg_id": infoleg_response.infoleg_id}
            llm_result = self.llm_service.process_text(primary_purified_text, context=context)

            if not llm_result.success:
                logger.log_processing_failed(
                    infoleg_id=infoleg_response.infoleg_id,
                    error=f"LLM structuring failed: {llm_result.error_message}",
                    error_type="llm_processing_failed"
                )

                # Store failed processing result to S3 for analysis
                failed_data = {
                    "infoleg_id": infoleg_response.infoleg_id,
                    "timestamp": datetime.now().isoformat(),
                    "error_type": "llm_processing_failed",
                    "error_message": llm_result.error_message,
                    "input_text": primary_purified_text[:1000],  # Truncate for storage
                    "primary_field": primary_field
                }
                self.storage_service.store_failed_processing(infoleg_response.infoleg_id, failed_data)

                self.stats['failed_llm_processing'] += 1
                return None

            logger.log_llm_call(
                infoleg_id=infoleg_response.infoleg_id,
                model=llm_result.model_used,
                tokens=llm_result.tokens_used,
                duration_ms=llm_result.processing_time * 1000 if llm_result.processing_time else None
            )

            # Step 3: Verification and quality control
            if llm_result.structured_data:
                logger.info(
                    "Starting verification",
                    stage=LogStage.VERIFICATION,
                    infoleg_id=infoleg_response.infoleg_id
                )

                is_valid, verification_message = self.verification_service.verify_structured_response(
                    primary_purified_text, llm_result.structured_data
                )

                if not is_valid:
                    logger.warning(
                        f"Verification failed: {verification_message}",
                        stage=LogStage.VERIFICATION,
                        infoleg_id=infoleg_response.infoleg_id,
                        verification_message=verification_message
                    )
                    self.stats['failed_verification'] += 1
                    # Continue processing despite verification failure for now
                    # In production, you might want to handle this differently, im looking at you Human Intervention Queue
                else:
                    logger.info(
                        "Verification passed",
                        stage=LogStage.VERIFICATION,
                        infoleg_id=infoleg_response.infoleg_id
                    )

            # Step 4: Update ProcessingData with LLM results
            # Create parsed text objects
            parsings = {}
            if llm_result.structured_data:
                parsings[primary_field] = ParsedText(
                    structured_data=llm_result.structured_data,
                    embeddings=None  # Will be filled by embedder
                )

            # Update existing processing_data with parsings
            input_data.processing_data.parsings = parsings

            # Update processor metadata with structuring info
            input_data.processing_data.processor_metadata.model_used = llm_result.model_used
            input_data.processing_data.processor_metadata.tokens_used += llm_result.tokens_used
            input_data.processing_data.processor_metadata.processing_timestamp = datetime.now().isoformat()

            # Store successful processing result to S3
            storage_key = f"processed_norms/{infoleg_response.infoleg_id}.json"
            try:
                logger.info(
                    "Storing processed norm to S3",
                    stage=LogStage.STORAGE_WRITE,
                    infoleg_id=infoleg_response.infoleg_id
                )
                stored = self.storage_service.store(storage_key, input_data.to_dict())
                if stored:
                    self.stats['stored_to_s3'] += 1
                else:
                    logger.warning(
                        "Failed to store to S3",
                        stage=LogStage.STORAGE_ERROR,
                        infoleg_id=infoleg_response.infoleg_id
                    )
            except Exception as storage_error:
                logger.error(
                    f"Error storing to S3: {storage_error}",
                    stage=LogStage.STORAGE_ERROR,
                    infoleg_id=infoleg_response.infoleg_id
                )
                # Continue anyway - storage failure shouldn't stop processing

            self.stats['successful'] += 1

            duration_ms = (time.time() - start_time) * 1000
            logger.log_processing_complete(
                infoleg_id=infoleg_response.infoleg_id,
                duration_ms=duration_ms,
                model_used=llm_result.model_used,
                tokens_used=input_data.processing_data.processor_metadata.tokens_used
            )

            return input_data

        except Exception as e:
            logger.log_processing_failed(
                infoleg_id=infoleg_response.infoleg_id if 'infoleg_response' in locals() else None,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    def is_available(self) -> bool:
        """Check if the parsing service is available"""
        return (
            self.text_processor is not None and
            self.llm_service.is_available() and
            self.verification_service is not None
        )

    def get_statistics(self) -> dict:
        """Get processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return self.stats

        success_rate = (self.stats['successful'] / total) * 100
        return {
            **self.stats,
            'success_rate': success_rate
        }