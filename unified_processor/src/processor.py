"""Main unified processor"""

import asyncio
import logging
import time
from typing import Dict, Any, List
import json

from .config import Config
from .database import DatabaseManager
from .text_processor import TextProcessor
from .llm_manager import LLMManager, ProcessingResult
from .email_service import EmailService
from .utils import RedisManager


class UnifiedProcessor:
    """Main processor that combines purification and LLM structuring"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.text_processor = TextProcessor()
        self.llm_manager = LLMManager(config)
        self.email_service = EmailService(config)
        self.redis_manager = RedisManager(config)
        self.logger = logging.getLogger(__name__)
        
        # Processing state
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.processed_count = 0
        self.failed_count = 0
        self.consecutive_failures = 0
        self.total_processing_time = 0.0
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(config.processing.max_concurrent_requests)
    
    async def run(self):
        """Main processing loop"""
        self.logger.info("Starting unified processing...")
        
        try:
            # Initialize Redis
            await self.redis_manager.initialize()
            
            # Get initial statistics
            await self.report_progress()
            
            # Main processing loop
            while True:
                # Get batch of unprocessed norms
                norms = await self.db_manager.get_unprocessed_norms(
                    limit=self.config.processing.batch_size
                )
                
                if not norms:
                    self.logger.info("No more norms to process")
                    break
                
                # Process batch concurrently
                tasks = [self.process_norm_with_semaphore(norm) for norm in norms]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Batch processing error for norm {norms[i]['id']}: {result}")
                        await self.handle_processing_failure(norms[i]['id'], str(result))
                
                # Check if we should report progress
                await self.check_and_report_progress()
                
                # Check for too many consecutive failures
                if self.consecutive_failures >= self.config.error_handling.max_consecutive_failures:
                    self.logger.error("Too many consecutive failures, pausing...")
                    await asyncio.sleep(self.config.error_handling.failure_cooldown)
                    self.consecutive_failures = 0
            
            # Final report
            await self.send_completion_report()
            
        except Exception as e:
            self.logger.error(f"Fatal error in processing loop: {e}", exc_info=True)
            await self.email_service.send_error_notification(str(e))
            raise
        finally:
            await self.redis_manager.close()
    
    async def process_norm_with_semaphore(self, norm: Dict[str, Any]):
        """Process a single norm with concurrency control"""
        async with self.semaphore:
            await self.process_norm(norm)
    
    async def process_norm(self, norm: Dict[str, Any]):
        """Process a single norm through the complete pipeline"""
        norm_id = norm['id']
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing norm {norm_id}")
            
            # Update status to processing
            await self.db_manager.update_processing_status(
                norm_id, 'processing'
            )
            
            # Step 1: Purify text and save to raw database
            purification_data = self.text_processor.purify_norm_with_tracking(norm)
            
            # Save purified data to raw database
            await self.db_manager.save_purified_norm(purification_data)
            
            # Extract data for LLM processing
            combined_text = purification_data['combined_text']
            
            # Check text length constraints
            if not combined_text or len(combined_text) < self.config.processing.min_text_length:
                raise Exception(f"Text too short or empty: {len(combined_text) if combined_text else 0} characters")
            
            if len(combined_text) > self.config.processing.max_text_length:
                self.logger.warning(f"Text too long ({len(combined_text)} chars), truncating...")
                combined_text = combined_text[:self.config.processing.max_text_length]
            
            # Step 2: LLM structuring with escalation
            system_prompt = self.llm_manager.get_system_prompt()
            purified_main_text = purification_data['purified_main_text']
            result = await self.llm_manager.process_with_escalation(
                combined_text, system_prompt, 
                similarity_reference_text=purified_main_text
            )
            
            if not result.success:
                raise Exception(result.error_message or "LLM processing failed")
            
            # Step 3: Prepare final data with ALL metadata augmentation
            structured_data = {
                'source_id': norm_id,
                
                # All original metadata fields (from original norm)
                'infoleg_id': purification_data.get('infoleg_id'),
                'jurisdiccion': purification_data.get('jurisdiccion'),
                'clase_norma': purification_data.get('clase_norma'),
                'tipo_norma': purification_data.get('tipo_norma'),
                'sancion': purification_data.get('sancion'),
                'id_normas': purification_data.get('id_normas'),
                'publicacion': purification_data.get('publicacion'),
                'titulo_sumario': purification_data.get('titulo_sumario'),
                'titulo_resumido': purification_data.get('titulo_resumido'),
                'observaciones': purification_data.get('observaciones'),
                'nro_boletin': purification_data.get('nro_boletin'),
                'pag_boletin': purification_data.get('pag_boletin'),
                'texto_resumido': purification_data.get('texto_resumido'),
                'estado': purification_data.get('estado'),
                'lista_normas_que_complementa': purification_data.get('lista_normas_que_complementa'),
                'lista_normas_que_la_complementan': purification_data.get('lista_normas_que_la_complementan'),
                
                # Original and purified text fields (augmented from purification step)
                'texto_norma': purification_data.get('texto_norma'),
                'texto_norma_actualizado': purification_data.get('texto_norma_actualizado'),
                'purified_texto_norma': purification_data.get('purified_main_text'),
                'purified_texto_norma_actualizado': purification_data.get('purified_updated_text'),
                
                # Purification metadata (augmented from purification step)
                'ocr_fixes_applied': purification_data.get('ocr_fixes_applied', []),
                
                # LLM Processing Results (augmented from LLM step)
                'llm_structured_json': result.structured_data,
                
                # Quality Control Data (augmented from quality control step)
                'text_similarity_score': result.text_similarity_score,
                'content_diff': result.content_diff,
                'quality_control_passed': result.quality_control_passed,
                'human_intervention_required': result.human_intervention_required,
                
                # Processing Metadata (augmented from processing step)
                'models_used': result.models_used or [result.model_used],
                'final_model_used': result.model_used,
                'processing_notes': f"LLM Processing completed with {result.model_used}"
            }
            
            # Step 4: Save to structured database
            await self.db_manager.save_structured_norm(structured_data)
            
            # Step 5: Update processing status
            processing_time = time.time() - start_time
            await self.db_manager.update_processing_status(
                norm_id, 
                'completed', 
                result.model_used,
                1,
                None,
                processing_time
            )
            
            # Update counters
            self.processed_count += 1
            self.total_processing_time += processing_time
            self.consecutive_failures = 0
            
            # Store processing metrics in Redis
            await self.redis_manager.store_processing_metrics(
                norm_id, result.model_used, processing_time, result.tokens_used
            )
            
            self.logger.info(f"Successfully processed norm {norm_id} with {result.model_used} in {processing_time:.2f}s")
            
        except Exception as e:
            await self.handle_processing_failure(norm_id, str(e))
    
    async def handle_processing_failure(self, norm_id: int, error_message: str):
        """Handle processing failure for a norm"""
        self.logger.error(f"Failed to process norm {norm_id}: {error_message}")
        
        # Get current status to check retry count
        status = await self.db_manager.get_processing_status(norm_id)
        attempts = (status['attempts'] if status else 0) + 1
        
        # Determine if this should be a permanent failure
        if attempts >= self.config.error_handling.max_item_retries:
            final_status = 'failed_permanently'
            self.logger.error(f"Norm {norm_id} failed permanently after {attempts} attempts")
        else:
            final_status = 'failed'
        
        # Update status
        await self.db_manager.update_processing_status(
            norm_id, final_status, None, attempts, error_message
        )
        
        # Update counters
        self.failed_count += 1
        self.consecutive_failures += 1
        
        # Send error notification for permanent failures
        if final_status == 'failed_permanently':
            await self.email_service.send_error_notification(error_message, str(norm_id))
    
    async def check_and_report_progress(self):
        """Check if it's time to report progress"""
        current_time = time.time()
        
        # Report every N processed items
        if self.processed_count > 0 and self.processed_count % self.config.processing.checkpoint_interval == 0:
            await self.report_progress()
        
        # Report based on time interval
        elif current_time - self.last_report_time >= self.config.processing.progress_report_interval:
            await self.report_progress()
    
    async def report_progress(self):
        """Generate and send progress report"""
        try:
            # Get current statistics
            stats = await self.db_manager.get_processing_stats()
            
            # Log progress
            total = stats.get('total', 0)
            completed = stats.get('completed', 0)
            completion_pct = (completed / total * 100) if total > 0 else 0
            
            self.logger.info(
                f"Progress: {completed:,}/{total:,} ({completion_pct:.1f}%) | "
                f"Processed this session: {self.processed_count:,} | "
                f"Failed this session: {self.failed_count:,}"
            )
            
            # Send email report
            elapsed_time = time.time() - self.start_time
            await self.email_service.send_progress_report(stats, elapsed_time)
            
            # Update last report time
            self.last_report_time = time.time()
            
        except Exception as e:
            self.logger.error(f"Error generating progress report: {e}")
    
    async def send_completion_report(self):
        """Send final completion report"""
        try:
            stats = await self.db_manager.get_processing_stats()
            total_time = time.time() - self.start_time
            
            self.logger.info("Processing completed!")
            self.logger.info(f"Total time: {total_time/3600:.1f} hours")
            self.logger.info(f"Final statistics: {stats}")
            
            await self.email_service.send_completion_notification(stats, total_time)
            
        except Exception as e:
            self.logger.error(f"Error sending completion report: {e}")