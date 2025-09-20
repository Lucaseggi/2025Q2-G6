"""Processing service that combines text purification and LLM parsing"""

import logging
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os

sys.path.append('/app/00-shared')
from rabbitmq_client import RabbitMQClient
from models import ScrapedData, ProcessedData, InfolegNorma

from text_processor import TextProcessor
from llm_manager import LLMManager, ProcessingResult
from config import ProcessingConfig
from s3_cache import ProcessorS3Cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main processor combining purification and LLM structuring"""

    def __init__(self):
        self.config = ProcessingConfig()
        self.text_processor = TextProcessor()
        self.llm_manager = LLMManager(self.config)
        self.queue_client = RabbitMQClient()

        # Initialize S3 cache
        self.cache = ProcessorS3Cache(
            bucket_name=os.getenv('PROCESSOR_S3_BUCKET', 'processor-cache'),
            endpoint_url=os.getenv('S3_ENDPOINT_URL')
        )

        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'dropped_json_validation': 0,
            'dropped_human_intervention': 0,
            'dropped_other_failures': 0,
            'queue_failures': 0,
        }

    def _purify_text_field(self, text: Optional[str], field_name: str, infoleg_id: int) -> Optional[str]:
        """Helper method to purify a single text field"""
        if not text or not text.strip():
            return None

        purified = self.text_processor.convert_html_to_structured_text(text)
        return purified if purified and purified.strip() else None

    def _log_processing_result(self, norma_id: int, success: bool, llm_results: Dict[str, Any] = None, failure_reason: str = None):
        """Log focused processing result with LLM response"""
        if success:
            logger.info(f"✓ SUCCESS: Norm {norma_id}")
            for field_name, result in llm_results.items():
                logger.info(f"  [{field_name}] Model: {result.get('model_used', 'unknown')}")
                logger.info(f"  [{field_name}] LLM Response: {json.dumps(result.get('structured_data', {}), indent=2, ensure_ascii=False)}")
        else:
            logger.error(f"✗ FAILURE: Norm {norma_id} - {failure_reason}")
            if llm_results:
                for field_name, result in llm_results.items():
                    # Handle both result objects and dicts
                    if hasattr(result, 'structured_data'):
                        logger.error(f"  [{field_name}] LLM Response: {json.dumps(result.structured_data, indent=2, ensure_ascii=False)}")
                    elif hasattr(result, 'raw_response'):
                        logger.error(f"  [{field_name}] LLM Raw Response: {result.raw_response}")
                    elif isinstance(result, dict) and 'structured_data' in result:
                        logger.error(f"  [{field_name}] LLM Response: {json.dumps(result['structured_data'], indent=2, ensure_ascii=False)}")

    def process_norma(self, scraped_data: ScrapedData) -> Optional[ProcessedData]:
        """Process a single norma through purification and LLM parsing"""
        try:
            norma = scraped_data.norma
            self.stats['total_processed'] += 1

            # Step 1: Text purification - process both fields individually
            purified_texto_norma = self._purify_text_field(
                norma.texto_norma, "texto_norma", norma.infoleg_id
            )

            # Process texto_norma_actualizado if exists and different from main text
            purified_texto_actualizado = None
            if (norma.texto_norma_actualizado and norma.texto_norma_actualizado.strip() and
                (not norma.texto_norma or norma.texto_norma_actualizado.strip() != norma.texto_norma.strip())):
                purified_texto_actualizado = self._purify_text_field(
                    norma.texto_norma_actualizado, "texto_norma_actualizado", norma.infoleg_id
                )

            # Check if we have any content to process
            if not purified_texto_norma and not purified_texto_actualizado:
                self._log_processing_result(norma.infoleg_id, False, None, "No content after purification")
                return None

            # Step 2: LLM processing for structuring - process each field separately
            llm_results = {}

            # Process texto_norma if available
            if purified_texto_norma:
                result = self.llm_manager.process_text_with_escalation(purified_texto_norma)
                if result.success:
                    # Check for critical failures that should drop the norm
                    if not result.json_validation_passed:
                        self.stats['dropped_json_validation'] += 1
                        self._log_processing_result(norma.infoleg_id, False,
                                                  {'texto_norma': result},
                                                  f"JSON validation failed - {result.json_validation_error}")
                        return None

                    # THIS WILL PUSH INTO HUMAN INTERENTION QUEUE IN THE NEAR FUTURE
                    if result.human_intervention_required:
                        self.stats['dropped_human_intervention'] += 1
                        self._log_processing_result(norma.infoleg_id, False,
                                                  {'texto_norma': result},
                                                  f"Human intervention required - quality control failed")
                        return None

                    # Success - store results
                    llm_results['texto_norma'] = {
                        'structured_data': result.structured_data,
                        'model_used': result.model_used,
                        'models_used': result.models_used,
                        'similarity_score': result.text_similarity_score,
                        'processing_time': result.processing_time,
                        'tokens_used': result.tokens_used,
                    }
                else:
                    self.stats['dropped_other_failures'] += 1
                    self._log_processing_result(norma.infoleg_id, False, None,
                                              f"LLM processing failed - {result.error_message}")
                    return None

            # Process texto_norma_actualizado if available
            if purified_texto_actualizado:
                result = self.llm_manager.process_text_with_escalation(purified_texto_actualizado)
                if result.success:
                    # Check for critical failures that should drop the norm
                    if not result.json_validation_passed:
                        self.stats['dropped_json_validation'] += 1
                        self._log_processing_result(norma.infoleg_id, False,
                                                  {'texto_norma_actualizado': result},
                                                  f"JSON validation failed - {result.json_validation_error}")
                        return None

                    if result.human_intervention_required:
                        self.stats['dropped_human_intervention'] += 1
                        self._log_processing_result(norma.infoleg_id, False,
                                                  {'texto_norma_actualizado': result},
                                                  f"Human intervention required - quality control failed")
                        return None

                    # Success - store results
                    llm_results['texto_norma_actualizado'] = {
                        'structured_data': result.structured_data,
                        'model_used': result.model_used,
                        'models_used': result.models_used,
                        'similarity_score': result.text_similarity_score,
                        'processing_time': result.processing_time,
                        'tokens_used': result.tokens_used,
                    }
                else:
                    self.stats['dropped_other_failures'] += 1
                    self._log_processing_result(norma.infoleg_id, False, None,
                                              f"LLM processing failed - {result.error_message}")
                    return None

            # Check if we have any successful LLM results
            if not llm_results:
                self.stats['dropped_other_failures'] += 1
                logger.error(
                    f"DROPPING NORM {norma.infoleg_id}: No text fields could be successfully processed"
                )
                return None

            # Update norma with processed fields
            norma.purified_texto_norma = purified_texto_norma
            norma.purified_texto_norma_actualizado = purified_texto_actualizado

            # Add structured data to norma
            if 'texto_norma' in llm_results:
                norma.structured_texto_norma = llm_results['texto_norma'][
                    'structured_data'
                ]
            if 'texto_norma_actualizado' in llm_results:
                norma.structured_texto_norma_actualizado = llm_results[
                    'texto_norma_actualizado'
                ]['structured_data']

            # Create ProcessedData object
            processed_data = ProcessedData(
                norma=norma, processing_timestamp=datetime.now().isoformat()
            )

            # Log comprehensive success information
            processed_fields = list(llm_results.keys())
            models_used = []
            for field_result in llm_results.values():
                models_used.extend(field_result.get('models_used', []))
            unique_models = list(set(models_used))

            # Determine overall human intervention requirement
            human_intervention_required = any(
                result.get('human_intervention_required', False)
                for result in llm_results.values()
            )

            self.stats['successful'] += 1
            self._log_processing_result(norma.infoleg_id, True, llm_results)

            # Cache the processed data
            try:
                self.cache.cache_processed_data(norma.infoleg_id, processed_data.to_dict())
            except Exception as e:
                logger.error(f"Cache error for norm {norma.infoleg_id}: {e}")

            return processed_data

        except Exception as e:
            self._log_processing_result(norma.infoleg_id, False, None, f"Processing exception - {str(e)}")
            return None

    def log_statistics(self):
        """Log current processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return

        success_rate = (self.stats['successful'] / total) * 100

        logger.info("=" * 80)
        logger.info("PROCESSING STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total processed:           {total}")
        logger.info(
            f"✓ Successful:              {self.stats['successful']} ({success_rate:.1f}%)"
        )
        logger.info(
            f"✗ JSON validation fails:   {self.stats['dropped_json_validation']}"
        )
        logger.info(
            f"✗ Human intervention req:  {self.stats['dropped_human_intervention']}"
        )
        logger.info(
            f"✗ Other failures:          {self.stats['dropped_other_failures']}"
        )
        logger.info(f"✗ Queue send failures:     {self.stats['queue_failures']}")
        logger.info("=" * 80)

    def run(self):
        """Main processing loop"""
        logger.info("Document Processor started - listening for scraped normas...")
        last_stats_log = time.time()

        while True:
            try:
                # Receive message from processing queue
                message = self.queue_client.receive_message('processing', timeout=20)

                if message:
                    # Parse scraped data
                    scraped_data = ScrapedData.from_dict(message)

                    # Process the norma
                    processed_data = self.process_norma(scraped_data)

                    if processed_data:
                        # Send to embedding queue
                        success = self.queue_client.send_message('embedding', processed_data.to_dict())
                        if not success:
                            self.stats['queue_failures'] += 1
                            logger.error(f"Queue failure: Could not send norm {processed_data.norma.infoleg_id} to embedding queue")

                # Log statistics every 5 minutes or after every 10 norms
                current_time = time.time()
                if (current_time - last_stats_log > 300) or (
                    self.stats['total_processed'] > 0
                    and self.stats['total_processed'] % 10 == 0
                ):
                    self.log_statistics()
                    last_stats_log = current_time

            except Exception as e:
                logger.error(f"Error in processing loop: {str(e)}")
                time.sleep(5)  # Wait before retrying


def main():
    """Main entry point - runs both queue processor and API server"""
    import threading
    from api import app

    # Initialize processor
    processor = DocumentProcessor()

    # Start queue processing in a separate thread
    processor_thread = threading.Thread(
        target=processor.run,
        name="QueueProcessor",
        daemon=True
    )

    # Start API server in a separate thread
    api_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=8004, debug=False),
        name="APIServer",
        daemon=True
    )

    logger.info("Starting processor service with both queue listener and API server...")

    # Start both threads
    processor_thread.start()
    api_thread.start()

    logger.info("Queue processor thread started")
    logger.info("API server thread started on port 8004")

    try:
        # Keep main thread alive
        while True:
            processor_thread.join(timeout=1.0)
            api_thread.join(timeout=1.0)

            # Check if threads are still alive
            if not processor_thread.is_alive():
                logger.error("Queue processor thread died, restarting...")
                processor_thread = threading.Thread(
                    target=processor.run,
                    name="QueueProcessor",
                    daemon=True
                )
                processor_thread.start()

            if not api_thread.is_alive():
                logger.error("API server thread died, restarting...")
                api_thread = threading.Thread(
                    target=lambda: app.run(host='0.0.0.0', port=8004, debug=False),
                    name="APIServer",
                    daemon=True
                )
                api_thread.start()

    except KeyboardInterrupt:
        logger.info("Shutting down processor service...")


if __name__ == "__main__":
    main()
