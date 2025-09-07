"""Processing service that combines text purification and LLM parsing"""

import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.append('/app/00-shared')
from queue_client import QueueClient
from models import ScrapedData, ProcessedData, InfolegNorma

from text_processor import TextProcessor
from simple_llm_manager import SimpleLLMManager, ProcessingResult
from config import ProcessingConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main processor combining purification and LLM structuring"""
    
    def __init__(self):
        self.config = ProcessingConfig()
        self.text_processor = TextProcessor()
        self.llm_manager = SimpleLLMManager(self.config)
        self.queue_client = QueueClient()
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'dropped_json_validation': 0,
            'dropped_human_intervention': 0,
            'dropped_other_failures': 0,
            'queue_failures': 0
        }
        
    def process_norma(self, scraped_data: ScrapedData) -> Optional[ProcessedData]:
        """Process a single norma through purification and LLM parsing"""
        try:
            norma = scraped_data.norma
            self.stats['total_processed'] += 1
            logger.info(f"Processing norma {norma.infoleg_id}: {norma.titulo_sumario[:50]}...")
            
            # Step 1: Text purification - process both fields individually
            purified_texto_norma = None
            purified_texto_actualizado = None
            
            # Process texto_norma if exists
            if norma.texto_norma and norma.texto_norma.strip():
                logger.info(f"Purifying texto_norma for norma {norma.infoleg_id}")
                purified_texto_norma = self.text_processor.convert_html_to_structured_text(norma.texto_norma)
                if not purified_texto_norma.strip():
                    purified_texto_norma = None
            
            # Process texto_norma_actualizado if exists and different
            if norma.texto_norma_actualizado and norma.texto_norma_actualizado.strip():
                if not norma.texto_norma or norma.texto_norma_actualizado.strip() != norma.texto_norma.strip():
                    logger.info(f"Purifying texto_norma_actualizado for norma {norma.infoleg_id}")
                    purified_texto_actualizado = self.text_processor.convert_html_to_structured_text(norma.texto_norma_actualizado)
                    if not purified_texto_actualizado.strip():
                        purified_texto_actualizado = None
            
            # Check if we have any content to process
            if not purified_texto_norma and not purified_texto_actualizado:
                logger.warning(f"No content after purification for norma {norma.infoleg_id}")
                return None
            
            # Step 2: LLM processing for structuring - process each field separately
            llm_results = {}
            
            # Process texto_norma if available
            if purified_texto_norma:
                logger.info(f"Processing texto_norma with LLM for norma {norma.infoleg_id}")
                result = self.llm_manager.process_text_with_escalation(purified_texto_norma)
                if result.success:
                    # Check for critical failures that should drop the norm
                    if not result.json_validation_passed:
                        self.stats['dropped_json_validation'] += 1
                        logger.error(f"DROPPING NORM {norma.infoleg_id}: JSON validation failed for texto_norma after all model attempts")
                        logger.error(f"JSON validation error: {result.json_validation_error}")
                        logger.error(f"Models attempted: {result.models_used}")
                        return None
                    
                    if result.human_intervention_required:
                        self.stats['dropped_human_intervention'] += 1
                        logger.error(f"DROPPING NORM {norma.infoleg_id}: Human intervention required for texto_norma - complexity too high")
                        logger.error(f"Quality control reason: {result.content_diff[:200]}...")
                        logger.error(f"Models attempted: {result.models_used}")
                        return None
                    
                    # Success - store results
                    llm_results['texto_norma'] = {
                        'structured_data': result.structured_data,
                        'similarity_score': result.text_similarity_score,
                        'content_diff': result.content_diff,
                        'quality_control_passed': result.quality_control_passed,
                        'human_intervention_required': result.human_intervention_required,
                        'json_validation_passed': result.json_validation_passed,
                        'json_validation_error': result.json_validation_error,
                        'model_used': result.model_used,
                        'models_used': result.models_used,
                        'processing_time': result.processing_time,
                        'tokens_used': result.tokens_used
                    }
                    logger.info(f"Successfully processed texto_norma for {norma.infoleg_id} with {result.model_used}")
                else:
                    self.stats['dropped_other_failures'] += 1
                    logger.error(f"DROPPING NORM {norma.infoleg_id}: LLM processing completely failed for texto_norma: {result.error_message}")
                    return None
            
            # Process texto_norma_actualizado if available
            if purified_texto_actualizado:
                logger.info(f"Processing texto_norma_actualizado with LLM for norma {norma.infoleg_id}")
                result = self.llm_manager.process_text_with_escalation(purified_texto_actualizado)
                if result.success:
                    # Check for critical failures that should drop the norm
                    if not result.json_validation_passed:
                        self.stats['dropped_json_validation'] += 1
                        logger.error(f"DROPPING NORM {norma.infoleg_id}: JSON validation failed for texto_norma_actualizado after all model attempts")
                        logger.error(f"JSON validation error: {result.json_validation_error}")
                        logger.error(f"Models attempted: {result.models_used}")
                        return None
                    
                    if result.human_intervention_required:
                        self.stats['dropped_human_intervention'] += 1
                        logger.error(f"DROPPING NORM {norma.infoleg_id}: Human intervention required for texto_norma_actualizado - complexity too high")
                        logger.error(f"Quality control reason: {result.content_diff[:200]}...")
                        logger.error(f"Models attempted: {result.models_used}")
                        return None
                    
                    # Success - store results
                    llm_results['texto_norma_actualizado'] = {
                        'structured_data': result.structured_data,
                        'similarity_score': result.text_similarity_score,
                        'content_diff': result.content_diff,
                        'quality_control_passed': result.quality_control_passed,
                        'human_intervention_required': result.human_intervention_required,
                        'json_validation_passed': result.json_validation_passed,
                        'json_validation_error': result.json_validation_error,
                        'model_used': result.model_used,
                        'models_used': result.models_used,
                        'processing_time': result.processing_time,
                        'tokens_used': result.tokens_used
                    }
                    logger.info(f"Successfully processed texto_norma_actualizado for {norma.infoleg_id} with {result.model_used}")
                else:
                    self.stats['dropped_other_failures'] += 1
                    logger.error(f"DROPPING NORM {norma.infoleg_id}: LLM processing completely failed for texto_norma_actualizado: {result.error_message}")
                    return None
            
            # Check if we have any successful LLM results
            if not llm_results:
                self.stats['dropped_other_failures'] += 1
                logger.error(f"DROPPING NORM {norma.infoleg_id}: No text fields could be successfully processed")
                return None
            
            # Step 3: Create combined content for chunking
            purified_parts = []
            if purified_texto_norma:
                purified_parts.append(("TEXTO ORIGINAL", purified_texto_norma.strip()))
            if purified_texto_actualizado:
                purified_parts.append(("TEXTO ACTUALIZADO", purified_texto_actualizado.strip()))
            
            purified_content = self._combine_purified_parts(purified_parts)
            
            # Create chunks from the best structured data available
            primary_structured_data = None
            if 'texto_norma_actualizado' in llm_results:
                primary_structured_data = llm_results['texto_norma_actualizado']['structured_data']
            elif 'texto_norma' in llm_results:
                primary_structured_data = llm_results['texto_norma']['structured_data']
            
            chunks = self._create_chunks(purified_content, primary_structured_data)
            
            # Determine overall human intervention requirement
            human_intervention_required = any(
                result.get('human_intervention_required', False) 
                for result in llm_results.values()
            )
            
            # Update norma with processed fields
            norma.purified_texto_norma = purified_texto_norma
            norma.purified_texto_norma_actualizado = purified_texto_actualizado
            
            # Add structured data to norma
            if 'texto_norma' in llm_results:
                norma.structured_texto_norma = llm_results['texto_norma']['structured_data']
            if 'texto_norma_actualizado' in llm_results:
                norma.structured_texto_norma_actualizado = llm_results['texto_norma_actualizado']['structured_data']
            
            # Create ProcessedData object with simplified structure
            processed_data = ProcessedData(
                norma=norma,
                processing_timestamp=datetime.now().isoformat()
            )
            
            # Log comprehensive success information
            processed_fields = list(llm_results.keys())
            models_used = []
            for field_result in llm_results.values():
                models_used.extend(field_result.get('models_used', []))
            unique_models = list(set(models_used))
            
            self.stats['successful'] += 1
            logger.info(f"✓ SUCCESSFULLY PROCESSED NORM {norma.infoleg_id}")
            logger.info(f"  ├─ Fields processed: {processed_fields}")
            logger.info(f"  ├─ Models used: {unique_models}")
            logger.info(f"  ├─ Human intervention required: {human_intervention_required}")
            logger.info(f"  ├─ Total chunks created: {len(chunks)}")
            logger.info(f"  └─ Content length: {len(purified_content)} chars")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing norma {norma.infoleg_id}: {str(e)}")
            return None
    
    def _combine_purified_parts(self, purified_parts: list) -> str:
        """Combine purified text parts with proper separators"""
        combined_parts = []
        
        for label, content in purified_parts:
            if len(purified_parts) > 1:
                combined_parts.append(f"=== {label} ===")
            combined_parts.append(content)
        
        return "\n\n".join(combined_parts)
    
    def _combine_text_fields(self, norma: InfolegNorma) -> str:
        """Legacy method - kept for compatibility"""
        content_parts = []
        
        if norma.texto_norma and norma.texto_norma.strip():
            content_parts.append(norma.texto_norma.strip())
        
        if norma.texto_norma_actualizado and norma.texto_norma_actualizado.strip():
            # Only add if different from texto_norma
            if norma.texto_norma_actualizado.strip() != norma.texto_norma.strip():
                content_parts.append("--- TEXTO ACTUALIZADO ---")
                content_parts.append(norma.texto_norma_actualizado.strip())
        
        return "\n\n".join(content_parts)
    
    def _create_chunks(self, purified_content: str, structured_data: Dict[str, Any]) -> list:
        """Create semantic chunks from the processed content"""
        # Simple chunking strategy - can be enhanced later
        max_chunk_size = 1000
        chunks = []
        
        # Add structured summary as first chunk
        if structured_data:
            summary_chunk = f"ESTRUCTURA: {structured_data}"
            chunks.append(summary_chunk)
        
        # Split content into chunks
        words = purified_content.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) + 1 > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def log_statistics(self):
        """Log current processing statistics"""
        total = self.stats['total_processed']
        if total == 0:
            return
            
        success_rate = (self.stats['successful'] / total) * 100
        
        logger.info("="*80)
        logger.info("PROCESSING STATISTICS")
        logger.info("="*80)
        logger.info(f"Total processed:           {total}")
        logger.info(f"✓ Successful:              {self.stats['successful']} ({success_rate:.1f}%)")
        logger.info(f"✗ JSON validation fails:   {self.stats['dropped_json_validation']}")
        logger.info(f"✗ Human intervention req:  {self.stats['dropped_human_intervention']}")
        logger.info(f"✗ Other failures:          {self.stats['dropped_other_failures']}")
        logger.info(f"✗ Queue send failures:     {self.stats['queue_failures']}")
        logger.info("="*80)
    
    def run(self):
        """Main processing loop"""
        logger.info("Document Processor started - listening for scraped normas...")
        last_stats_log = time.time()
        
        while True:
            try:
                # Receive message from processing queue
                message = self.queue_client.receive_message('processing', wait_time=20)
                
                if message:
                    logger.info("Received scraped data for processing")
                    
                    # Parse scraped data
                    scraped_data = ScrapedData.from_dict(message)
                    
                    # Process the norma
                    processed_data = self.process_norma(scraped_data)
                    
                    if processed_data:
                        # Send to embedding queue
                        success = self.queue_client.send_message('embedding', processed_data.to_dict())
                        if success:
                            logger.info(f"✓ QUEUED FOR EMBEDDING: Norma {processed_data.norma.infoleg_id} sent to embedding queue")
                        else:
                            self.stats['queue_failures'] += 1
                            logger.error(f"✗ QUEUE FAILURE: Failed to send processed norma {processed_data.norma.infoleg_id} to embedding queue")
                    else:
                        # Norm was dropped due to processing failures
                        norma_data = ScrapedData.from_dict(message)
                        logger.error(f"✗ NORM DROPPED: Failed to process norma {norma_data.norma.infoleg_id}")
                        logger.error(f"  └─ Reason: JSON validation failure or human intervention required")
                        logger.error(f"  └─ This norm requires specialized handling or manual review")
                
                # Log statistics every 5 minutes or after every 10 norms
                current_time = time.time()
                if (current_time - last_stats_log > 300) or (self.stats['total_processed'] > 0 and self.stats['total_processed'] % 10 == 0):
                    self.log_statistics()
                    last_stats_log = current_time
                
            except Exception as e:
                logger.error(f"Error in processing loop: {str(e)}")
                time.sleep(5)  # Wait before retrying


def main():
    processor = DocumentProcessor()
    processor.run()


if __name__ == "__main__":
    main()