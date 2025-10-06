"""Parsing service implementation that orchestrates text processing, LLM, and verification"""

import logging
import json
from datetime import datetime
from typing import Optional
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from models import ProcessedData, ProcessingData, ProcessorMetadata, ParsedText

# Add src to path for interfaces
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from interfaces.parsing_service_interface import ParsingServiceInterface
from interfaces.text_processing_interface import TextProcessingInterface
from interfaces.llm_service_interface import LLMServiceInterface
from interfaces.verification_service_interface import VerificationServiceInterface
from interfaces.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


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
        self.logger = logging.getLogger(__name__)

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
        try:
            # Get InfolegApiResponse from scraping data
            infoleg_response = input_data.scraping_data.infoleg_response
            self.stats['total_processed'] += 1

            self.logger.info(f"Processing document {infoleg_response.infoleg_id}")

            # Step 1: Text purification - prioritize texto_norma_actualizado
            purified_original = None
            purified_updated = None
            primary_field = None
            primary_purified_text = None

            # Check if texto_norma_actualizado exists and has content
            if infoleg_response.texto_norma_actualizado and infoleg_response.texto_norma_actualizado.strip():
                purified_updated = self.text_processor.purify_text(infoleg_response.texto_norma_actualizado)
                if purified_updated and self.text_processor.is_valid_text(purified_updated):
                    primary_field = "updated_text"
                    primary_purified_text = purified_updated

            # Fall back to texto_norma only if texto_norma_actualizado is not available
            if not primary_purified_text and infoleg_response.texto_norma and infoleg_response.texto_norma.strip():
                purified_original = self.text_processor.purify_text(infoleg_response.texto_norma)
                if purified_original and self.text_processor.is_valid_text(purified_original):
                    primary_field = "original_text"
                    primary_purified_text = purified_original

            # Check if we have any content to process
            if not primary_purified_text:
                self.logger.error(f"No valid content after purification")
                self.stats['failed_purification'] += 1

                # Create minimal ProcessingData without LLM processing
                processor_metadata = ProcessorMetadata(
                    model_used="none",
                    tokens_used=0,
                    processing_timestamp=datetime.now().isoformat()
                )

                processing_data = ProcessingData(
                    purifications={
                        "original_text": purified_original or "",
                        "updated_text": purified_updated or ""
                    },
                    parsings={},
                    processor_metadata=processor_metadata,
                    embedder_metadata=None
                )

                input_data.processing_data = processing_data
                return input_data

            # Step 2: LLM processing for structuring
            self.logger.info(f"Processing {primary_field} for document {infoleg_response.infoleg_id}")

            # Pass context with infoleg_id for better logging
            context = {"infoleg_id": infoleg_response.infoleg_id}
            llm_result = self.llm_service.process_text(primary_purified_text, context=context)

            if not llm_result.success:
                self.logger.error(f"Input text: {primary_purified_text[:500]}...")
                if "Failed to parse JSON" in llm_result.error_message:
                    self.logger.error("Response was not valid JSON output")
                else:
                    self.logger.error(f"LLM processing failed: {llm_result.error_message}")

                # Store failed processing result to S3 for analysis
                failed_data = {
                    "infoleg_id": infoleg_response.infoleg_id,
                    "timestamp": datetime.now().isoformat(),
                    "error_type": "llm_processing_failed",
                    "error_message": llm_result.error_message,
                    "input_text": primary_purified_text,
                    "primary_field": primary_field
                }
                self.storage_service.store_failed_processing(infoleg_response.infoleg_id, failed_data)

                self.stats['failed_llm_processing'] += 1
                return None

            # Step 3: Verification and quality control
            if llm_result.structured_data:

                is_valid, verification_message = self.verification_service.verify_structured_response(
                    primary_purified_text, llm_result.structured_data
                )

                if not is_valid:
                    # Log input text and output only when verification fails
                    self.logger.error(f"Input text: {primary_purified_text[:500]}...")
                    if "JSON validation failed" in verification_message:
                        self.logger.error(f"Validation failed: {verification_message}")
                        self.logger.error(f"Failed JSON response: {llm_result.raw_response}")
                    elif "Similarity score" in verification_message:
                        self.logger.error(f"Quality Control not passed: {verification_message}")
                        self.logger.error(f"Failed structured data: {json.dumps(llm_result.structured_data, indent=2, ensure_ascii=False)}")
                    else:
                        self.logger.error(f"Verification failed: {verification_message}")
                        self.logger.error(f"Failed response: {llm_result.raw_response}")
                    self.stats['failed_verification'] += 1
                    # Continue processing despite verification failure for now
                    # In production, you might want to handle this differently, im looking at you Human Intervention Queue

            # Step 4: Create ProcessingData with results
            processor_metadata = ProcessorMetadata(
                model_used=llm_result.model_used,
                tokens_used=llm_result.tokens_used,
                processing_timestamp=datetime.now().isoformat()
            )

            # Create parsed text objects
            parsings = {}
            if llm_result.structured_data:
                parsings[primary_field] = ParsedText(
                    structured_data=llm_result.structured_data,
                    embeddings=None  # Will be filled by embedder
                )

            processing_data = ProcessingData(
                purifications={
                    "original_text": purified_original or "",
                    "updated_text": purified_updated or ""
                },
                parsings=parsings,
                processor_metadata=processor_metadata,
                embedder_metadata=None
            )

            # Add processing data to existing structure
            input_data.processing_data = processing_data

            # Store successful processing result to S3
            storage_key = f"processed_norms/{infoleg_response.infoleg_id}.json"
            try:
                stored = self.storage_service.store(storage_key, input_data.to_dict())
                if stored:
                    self.stats['stored_to_s3'] += 1
                    self.logger.debug(f"Stored processed norm {infoleg_response.infoleg_id} to S3")
                else:
                    self.logger.warning(f"Failed to store processed norm {infoleg_response.infoleg_id} to S3")
            except Exception as storage_error:
                self.logger.error(f"Error storing to S3: {storage_error}")
                # Continue anyway - storage failure shouldn't stop processing

            self.stats['successful'] += 1
            return input_data

        except Exception as e:
            self.logger.error(f"Processing error: {e}")
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