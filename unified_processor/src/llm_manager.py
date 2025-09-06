"""LLM management with model escalation and API key rotation"""

import asyncio
import logging
import json
import time
import difflib
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import Config


@dataclass
class ProcessingResult:
    """Result of LLM processing"""
    success: bool
    structured_data: Optional[Dict[str, Any]] = None
    model_used: str = ""
    models_used: List[str] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    tokens_used: int = 0
    text_similarity_score: float = 0.0
    content_diff: str = ""
    quality_control_passed: bool = False
    human_intervention_required: bool = False


class APIKeyManager:
    """Manages API key rotation and rate limiting"""
    
    def __init__(self, api_keys: List[str], rate_limit: int):
        self.api_keys = api_keys
        self.rate_limit = rate_limit  # requests per minute
        self.current_key_index = 0
        self.request_times = {key: [] for key in api_keys}
        self.logger = logging.getLogger(__name__)
        
        # Log API key information (masked for security)
        self.logger.info(f"Initialized with {len(api_keys)} API keys")
        for i, key in enumerate(api_keys):
            if key and len(key) > 8:
                masked_key = key[:4] + "..." + key[-4:]
            else:
                masked_key = "INVALID_OR_EMPTY"
            self.logger.info(f"API Key {i+1}: {masked_key}")
    
    async def get_available_key(self) -> str:
        """Get an available API key that hasn't exceeded rate limits"""
        current_time = time.time()
        
        # Try each key starting from current index
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_key_index]
            
            # Clean old request times (older than 1 minute)
            self.request_times[key] = [
                req_time for req_time in self.request_times[key]
                if current_time - req_time < 60
            ]
            
            # Check if key is available
            if len(self.request_times[key]) < self.rate_limit:
                self.request_times[key].append(current_time)
                masked_key = key[:4] + "..." + key[-4:] if key and len(key) > 8 else "INVALID"
                self.logger.info(f"Using API key: {masked_key}")
                return key
            
            # Move to next key
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        # All keys exhausted, wait for the oldest request to expire
        min_wait_time = float('inf')
        for key_times in self.request_times.values():
            if key_times:
                oldest_request = min(key_times)
                wait_time = 60 - (current_time - oldest_request)
                min_wait_time = min(min_wait_time, wait_time)
        
        if min_wait_time > 0:
            self.logger.info(f"All API keys rate limited. Waiting {min_wait_time:.2f} seconds")
            await asyncio.sleep(min_wait_time)
            return await self.get_available_key()
        
        # Return first key as fallback
        return self.api_keys[0]


class LLMManager:
    """Manages LLM interactions with intelligent model escalation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_key_manager = APIKeyManager(
            config.gemini.api_keys, 
            config.gemini.rate_limit
        )
        self.logger = logging.getLogger(__name__)
        
        # Configure safety settings
        self.safety_settings = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        }
    
    def _calculate_text_similarity(self, original: str, structured: str) -> float:
        """Calculate content-focused similarity between original and structured text"""
        # Clean the JSON response
        clean_json = structured.strip()
        if clean_json.startswith('```json'):
            clean_json = clean_json[7:]
        if clean_json.endswith('```'):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()
        
        try:
            data = json.loads(clean_json)
            extracted_text = self._extract_structured_text(data)
        except Exception as e:
            self.logger.warning(f"Failed to parse JSON for similarity: {e}")
            return 0.0
        
        # Use content-focused similarity instead of character-level
        similarity = self._calculate_content_similarity(original, extracted_text)
        
        # Debug logging
        original_clean = self._clean_text_for_comparison(original)
        extracted_clean = self._clean_text_for_comparison(extracted_text)
        self.logger.info(f"DEBUG: Original clean ({len(original_clean)} chars): '{original_clean[:300]}...'")
        self.logger.info(f"DEBUG: Extracted clean ({len(extracted_clean)} chars): '{extracted_clean[:300]}...'")
        self.logger.info(f"DEBUG: Content similarity score: {similarity:.4f}")
        
        return similarity
    
    def _calculate_content_similarity(self, original: str, extracted: str) -> float:
        """Calculate content-focused similarity using word-level analysis"""
        # Normalize both texts
        original_words = self._extract_content_words(original)
        extracted_words = self._extract_content_words(extracted)
        
        # Calculate word-level similarity
        matcher = difflib.SequenceMatcher(None, original_words, extracted_words)
        word_similarity = matcher.ratio()
        
        # Calculate word set similarity (Jaccard similarity)
        original_set = set(original_words)
        extracted_set = set(extracted_words)
        if not original_set and not extracted_set:
            set_similarity = 1.0
        elif not original_set or not extracted_set:
            set_similarity = 0.0
        else:
            intersection = original_set.intersection(extracted_set)
            union = original_set.union(extracted_set)
            set_similarity = len(intersection) / len(union)
        
        # Detect potential hallucination by checking for added content
        original_set = set(original_words)
        extracted_set = set(extracted_words)
        added_words = extracted_set - original_set
        
        # Calculate hallucination penalty based on new words
        hallucination_penalty = 1.0
        if len(added_words) > 0:
            # Penalty based on ratio of new words to original content
            added_ratio = len(added_words) / max(len(original_words), 1)
            if added_ratio > 0.05:  # More than 5% new words
                # Strong penalty for potential hallucination
                hallucination_penalty = max(0.4, 1.0 - (added_ratio * 3.0))
                self.logger.info(f"DEBUG: Hallucination penalty - added words: {len(added_words)}, ratio: {added_ratio:.3f}, penalty: {hallucination_penalty:.3f}")
        
        # Length penalty for significantly shorter content (truncation detection)
        length_ratio = len(extracted_words) / max(len(original_words), 1)
        length_penalty = 1.0
        if length_ratio < 0.8:  # More than 20% shorter
            missing_ratio = 0.8 - length_ratio
            length_penalty = max(0.3, 1.0 - (missing_ratio * 2.0))
            self.logger.info(f"DEBUG: Truncation penalty - ratio: {length_ratio:.3f}, penalty: {length_penalty:.3f}")
        
        # Weighted combination (favor word order but also consider content coverage)
        combined_similarity = (word_similarity * 0.7) + (set_similarity * 0.3)
        
        # Apply both penalties
        final_similarity = combined_similarity * hallucination_penalty * length_penalty
        
        self.logger.info(f"DEBUG: Word similarity: {word_similarity:.4f}, Set similarity: {set_similarity:.4f}")
        self.logger.info(f"DEBUG: Length ratio: {length_ratio:.3f}, Final similarity: {final_similarity:.4f}")
        
        return final_similarity
    
    def _extract_content_words(self, text: str) -> list:
        """Extract meaningful content words, filtering out structural elements"""
        # Basic text cleaning
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Filter out article headers and structural words
        content_words = []
        skip_patterns = [
            r'^artículo$', r'^articulo$', r'^art\.$',  # Article headers
            r'^\d+[°\.]*$',  # Standalone numbers  
            r'^[-–—]+$',     # Dashes
            r'^\.$', r'^,$', r'^;$', r'^:$'  # Standalone punctuation
        ]
        
        for word in words:
            # Skip if word matches any skip pattern
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, word):
                    skip = True
                    break
            
            if not skip and len(word) > 1:  # Skip single characters
                # Clean the word of trailing punctuation but keep meaningful parts
                cleaned_word = re.sub(r'[^\w]$', '', word)
                if cleaned_word:
                    content_words.append(cleaned_word)
        
        return content_words
    
    def _extract_structured_text(self, data: dict) -> str:
        """Extract only content text from JSON structure (excludes metadata like numbers)"""
        text_parts = []
        
        # 1. Preamble - initial section content only
        preamble = data.get('preamble', '')
        if preamble and preamble.strip():
            text_parts.append(preamble.strip())
        
        # 2. Articles - only body content, skip numbers
        articles = data.get('articles', [])
        if isinstance(articles, list):
            for article in articles:
                if isinstance(article, dict):
                    article_text = article.get('body', '')
                    if article_text and article_text.strip():
                        text_parts.append(article_text.strip())
        
        # 3. Postamble - text after articles content only
        postamble = data.get('postamble', '')
        if postamble and postamble.strip():
            text_parts.append(postamble.strip())
        
        # 4. Short document - for documents without preamble/articles structure
        short_document = data.get('short_document', '')
        if short_document and short_document.strip():
            text_parts.append(short_document.strip())
        
        # 5. Firms - signatures and official names content only
        firms = data.get('firms', '')
        if firms and firms.strip():
            text_parts.append(firms.strip())
        
        # 6. Referenced articles text (only body content, skip metadata)
        references = data.get('references', [])
        if isinstance(references, list):
            for ref in references:
                if isinstance(ref, dict):
                    ref_articles = ref.get('articles', [])
                    if isinstance(ref_articles, list):
                        for ref_article in ref_articles:
                            if isinstance(ref_article, dict):
                                ref_article_text = ref_article.get('body', '')
                                if ref_article_text and ref_article_text.strip():
                                    text_parts.append(ref_article_text.strip())
        
        return ' '.join(text_parts)
    
    def _clean_text_for_comparison(self, text: str) -> str:
        """Clean text for similarity comparison"""
        # Convert to lowercase first
        text = text.lower()
        
        # Remove common prefixes/headers
        text = re.sub(r'^texto norma:\s*', '', text)
        text = re.sub(r'^texto norma actualizado:\s*', '', text)
        
        # Normalize whitespace and line breaks
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common separators and formatting
        text = re.sub(r'-{2,}', '', text)  # Remove ---- separators
        text = re.sub(r'[°\.]\s*', ' ', text)  # N° -> N 
        
        return text.strip()
    
    def _extract_all_text_from_json(self, data: Any) -> str:
        """Recursively extract all text from JSON structure with proper spacing"""
        text_parts = []
        self._collect_text_parts(data, text_parts)
        
        # Join with spaces and clean up
        result = ' '.join(text_parts)
        # Replace multiple spaces with single space
        result = re.sub(r'\s+', ' ', result)
        return result.strip()
    
    def _collect_text_parts(self, data: Any, text_parts: List[str]):
        """Recursively collect text from data structure"""
        if isinstance(data, dict):
            for key, value in data.items():
                # Skip certain metadata keys that don't contain content
                if key in ['number']:
                    continue
                self._collect_text_parts(value, text_parts)
        elif isinstance(data, list):
            for item in data:
                self._collect_text_parts(item, text_parts)
        elif isinstance(data, str) and data.strip():
            # Clean up the text part
            clean_text = data.strip()
            # Remove JSON formatting artifacts
            clean_text = clean_text.replace('```json', '').replace('```', '')
            if clean_text:
                text_parts.append(clean_text)
    
    def _normalize_text_for_comparison(self, text: str) -> str:
        """Normalize text for similarity comparison"""
        if not text:
            return ""
        
        # Convert to lowercase for case-insensitive comparison
        text = text.lower()
        
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common punctuation that might vary
        text = re.sub(r'[""''`´]', '"', text)  # Normalize quotes
        text = re.sub(r'[–—−]', '-', text)      # Normalize dashes
        
        # Remove number formatting that might vary (like "N°" vs "N.")
        text = re.sub(r'n[°\.]\s*', 'n ', text)
        
        # Remove extra punctuation at word boundaries
        text = re.sub(r'\s*[.,:;]\s*', ' ', text)
        
        # Clean up and return
        return text.strip()
    
    def _extract_text_from_dict(self, data: Any, text_parts: List[str]):
        """Legacy method - kept for compatibility with other functions"""
        if isinstance(data, dict):
            for value in data.values():
                self._extract_text_from_dict(value, text_parts)
        elif isinstance(data, list):
            for item in data:
                self._extract_text_from_dict(item, text_parts)
        elif isinstance(data, str) and data.strip():
            text_parts.append(data.strip())
    
    def _should_escalate_model(self, original_text: str, structured_result: str) -> bool:
        """Determine if model should be escalated based on text similarity"""
        similarity = self._calculate_text_similarity(original_text, structured_result)
        
        # If similarity is too low, escalate
        threshold = self.config.gemini.diff_threshold
        should_escalate = similarity < (1.0 - threshold)
        
        if should_escalate:
            self.logger.info(f"Similarity {similarity:.3f} below threshold {1.0 - threshold:.3f}, escalating model")
        
        return should_escalate
    
    def _generate_content_diff(self, original_text: str, structured_text: str) -> str:
        """Generate a readable diff between original and structured text"""
        # Extract text from structured JSON using the proper extraction method
        try:
            clean_json = structured_text.strip()
            if clean_json.startswith('```json'):
                clean_json = clean_json[7:]
            if clean_json.endswith('```'):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            structured_data = json.loads(clean_json)
            extracted_text = self._extract_structured_text(structured_data)
        except Exception as e:
            self.logger.warning(f"Failed to extract text from JSON for diff: {e}")
            extracted_text = structured_text
        
        # Clean both texts for comparison
        original_clean = self._clean_text_for_comparison(original_text)
        extracted_clean = self._clean_text_for_comparison(extracted_text)
        
        # Generate unified diff
        original_lines = original_clean.splitlines()
        extracted_lines = extracted_clean.splitlines()
        
        diff_lines = list(difflib.unified_diff(
            original_lines, 
            extracted_lines, 
            fromfile='original', 
            tofile='llm_extracted',
            lineterm=''
        ))
        
        return '\n'.join(diff_lines)
    
    async def _perform_quality_control(
        self, 
        original_text: str, 
        structured_result: str,
        api_key: str
    ) -> Tuple[bool, bool, str]:
        """Perform second-level quality control using another model call"""
        try:
            # First check similarity - if perfect, no QC needed
            similarity = self._calculate_text_similarity(original_text, structured_result)
            if similarity == 1.0:
                return True, False, f"Perfect similarity ({similarity:.3f}) - content perfectly preserved"
            
            # If similarity is very high but not perfect, we still need to check what changed
            if similarity < 0.85:
                return False, True, f"Low similarity ({similarity:.3f}) - major changes detected"
            
            # Generate diff for analysis using our cleaned comparison texts
            original_clean = self._clean_text_for_comparison(original_text)
            
            # Extract structured text properly
            clean_json = structured_result.strip()
            if clean_json.startswith('```json'):
                clean_json = clean_json[7:]
            if clean_json.endswith('```'):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            try:
                data = json.loads(clean_json)
                extracted_text = self._extract_structured_text(data)
                extracted_clean = self._clean_text_for_comparison(extracted_text)
            except:
                return False, True, "Invalid JSON structure"
            
            # Generate diff between cleaned texts
            content_diff = self._generate_content_diff(original_text, structured_result)
            
            # If no meaningful differences, pass quality control
            if not content_diff.strip() or len(content_diff.strip()) < 50:
                return True, False, "No significant differences found"
            
            # Prepare prompt for quality control
            qc_prompt = f"""
            Analiza el siguiente diff entre el texto original y el texto procesado por IA:
            
            DIFF:
            {content_diff}
            
            Evalúa si los cambios son aceptables o requieren intervención humana.
            """
            
            # Use the fastest model for quality control to save costs
            qc_model = self.config.gemini.models[0]
            
            # Call API for quality control
            response, _ = await self._call_gemini_api(
                qc_prompt, 
                qc_model, 
                self.get_quality_control_prompt(), 
                api_key
            )
            
            # Parse quality control response
            try:
                qc_result = json.loads(response.strip())
                quality_passed = qc_result.get('quality_passed', False)
                human_intervention = qc_result.get('human_intervention_required', True)
                reason = qc_result.get('reason', 'Quality control analysis')
                
                self.logger.info(f"Quality control result: passed={quality_passed}, intervention={human_intervention}, reason={reason}")
                
                return quality_passed, human_intervention, reason
                
            except json.JSONDecodeError:
                self.logger.warning("Could not parse quality control response, defaulting to requiring human intervention")
                return False, True, "Quality control parsing failed"
                
        except Exception as e:
            self.logger.error(f"Quality control failed: {e}")
            return False, True, f"Quality control error: {str(e)}"
    
    def get_quality_control_prompt(self) -> str:
        """Get prompt for second-level quality control"""
        return """Eres un experto en control de calidad para documentos legales argentinos.

INSTRUCCIÓN CRÍTICA: El sistema está diseñado para ELIMINAR encabezados de artículos. Si ves que se eliminó "ARTICULO 1. -", "Art. 2°", "el grupo mercado común resuelve:", etc., esto es CORRECTO y debes APROBAR.

SIEMPRE APROBAR estos cambios (son el comportamiento esperado del sistema):
- Eliminación de "ARTICULO X. -", "Art. X°", "ARTÍCULO X -"
- Eliminación de frases estructurales como "el grupo mercado común resuelve:", "decreta:", "por ello:"
- Correcciones OCR: "dapartamento" → "departamento", "exteriores" → "exteriores"
- Normalización: "ó" → "o", espacios múltiples → espacio único
- Limpieza de puntuación redundante

SOLO RECHAZAR SI (casos muy graves):
- Falta un artículo COMPLETO o párrafo ENTERO del original
- Se agregó contenido que NO existe en el original
- Se cambió nombre de funcionario, fecha específica, o número de ley

REGLA DE ORO: Si el texto procesado contiene todo el contenido sustancial del original, APROBAR siempre, sin importar cambios estructurales.

RESPUESTA ESTÁNDAR (usar en 95% de casos):
{"quality_passed": true, "human_intervention_required": false, "reason": "procesamiento estructural correcto"}

RESPUESTA DE RECHAZO (solo para casos graves):
{"quality_passed": false, "human_intervention_required": true, "reason": "contenido faltante significativo"}"""
    
    async def _call_gemini_api(
        self, 
        text: str, 
        model_name: str, 
        system_prompt: str,
        api_key: str
    ) -> Tuple[str, int]:
        """Call Gemini API with retry logic"""
        for attempt in range(3):
            try:
                self.logger.info(f"Calling Gemini API - Model: {model_name}, Attempt: {attempt + 1}")
                
                # Configure the API key
                genai.configure(api_key=api_key)
                
                # Initialize model with system instruction
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt
                )
                
                # Configure generation settings
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=self.config.gemini.max_output_tokens,
                    temperature=0.1,
                    top_p=1.0,
                )
                
                # Generate response
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content(
                        text,
                        generation_config=generation_config,
                        safety_settings=self.safety_settings
                    )
                )
                
                if not response.text:
                    self.logger.error(f"Empty response from Gemini API - Model: {model_name}")
                    self.logger.error(f"Response object: {response}")
                    self.logger.error(f"Response candidates: {getattr(response, 'candidates', 'N/A')}")
                    self.logger.error(f"Response finish_reason: {getattr(response, 'finish_reason', 'N/A')}")
                    raise Exception("Empty response from Gemini API")
                
                # Estimate token usage (rough approximation)
                tokens_used = len(text.split()) + len(response.text.split())
                
                self.logger.info(f"Successfully got response from {model_name}, tokens: {tokens_used}")
                return response.text, tokens_used
                
            except Exception as e:
                self.logger.error(f"Gemini API call failed - Model: {model_name}, Attempt: {attempt + 1}")
                self.logger.error(f"Exception type: {type(e).__name__}")
                self.logger.error(f"Exception message: {str(e)}")
                self.logger.error(f"Full exception: {e}", exc_info=True)
                
                if hasattr(e, 'response'):
                    self.logger.error(f"API response: {e.response}")
                if hasattr(e, 'details'):
                    self.logger.error(f"API details: {e.details}")
                if hasattr(e, 'message'):
                    self.logger.error(f"API message: {e.message}")
                
                if attempt == 2:  # Last attempt
                    raise e
                
                # Wait before retrying
                wait_time = 2 ** attempt
                self.logger.info(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
    
    async def process_with_escalation(
        self, 
        text: str, 
        system_prompt: str,
        max_models: int = None,
        similarity_reference_text: str = None
    ) -> ProcessingResult:
        """Process text with model escalation if needed"""
        start_time = time.time()
        models_to_try = self.config.gemini.models[:max_models] if max_models else self.config.gemini.models
        
        # Debug: Log the original text (first 1000 chars)
        self.logger.info("="*80)
        self.logger.info("DEBUG: ORIGINAL TEXT INPUT")
        self.logger.info("="*80)
        original_preview = text[:1000] + "..." if len(text) > 1000 else text
        self.logger.info(f"Original text ({len(text)} chars):\n{original_preview}")
        self.logger.info("="*80)
        
        last_error = None
        
        for model_index, model_name in enumerate(models_to_try):
            try:
                self.logger.info(f"Attempting processing with model: {model_name}")
                
                # Get available API key
                api_key = await self.api_key_manager.get_available_key()
                
                # Call API
                result_text, tokens_used = await self._call_gemini_api(
                    text, model_name, system_prompt, api_key
                )
                
                # Debug: Log the model response
                self.logger.info("-"*80)
                self.logger.info(f"DEBUG: {model_name.upper()} RESPONSE")
                self.logger.info("-"*80)
                response_preview = result_text[:2000] + "..." if len(result_text) > 2000 else result_text
                self.logger.info(f"Response ({len(result_text)} chars):\n{response_preview}")
                self.logger.info("-"*80)
                
                # Parse result
                try:
                    structured_data = json.loads(result_text.strip())
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        structured_data = json.loads(result_text[json_start:json_end])
                    else:
                        raise Exception("Invalid JSON response")
                
                # Calculate similarity for debug logging using reference text if provided
                reference_text = similarity_reference_text if similarity_reference_text is not None else text
                similarity_score = self._calculate_text_similarity(reference_text, result_text)
                self.logger.info(f"DEBUG: Text similarity score: {similarity_score:.4f}")
                if similarity_reference_text is not None:
                    self.logger.info("DEBUG: Using purified_texto_norma for similarity calculation")
                
                # Show the extracted and normalized texts for debugging
                try:
                    if result_text.strip().startswith('{'):
                        structured_data_debug = json.loads(result_text.strip())
                        extracted_debug = self._extract_all_text_from_json(structured_data_debug)
                        original_norm = self._normalize_text_for_comparison(text)
                        extracted_norm = self._normalize_text_for_comparison(extracted_debug)
                        
                        self.logger.info(f"DEBUG: Original normalized: {original_norm[:300]}...")
                        self.logger.info(f"DEBUG: Extracted text: {extracted_debug[:300]}...")
                        self.logger.info(f"DEBUG: Extracted normalized: {extracted_norm[:300]}...")
                except Exception as e:
                    self.logger.warning(f"DEBUG: Could not extract text for comparison: {e}")
                
                # Check if we should escalate to next model
                if model_index < len(models_to_try) - 1:
                    if self._should_escalate_model(reference_text, result_text):
                        self.logger.info(f"DEBUG: Escalating from {model_name} to {models_to_try[model_index + 1]} due to low similarity")
                        continue
                    else:
                        self.logger.info(f"DEBUG: Similarity acceptable, using {model_name} result")
                
                # Perform quality control
                content_diff = self._generate_content_diff(reference_text, result_text)
                
                # Skip LLM quality control if similarity is very high
                if similarity_score >= 0.9:
                    quality_passed = True
                    human_intervention = False
                    qc_reason = f"Very high similarity ({similarity_score:.3f}) - direct approval"
                else:
                    quality_passed, human_intervention, qc_reason = await self._perform_quality_control(
                        reference_text, result_text, api_key
                    )
                
                # Success
                processing_time = time.time() - start_time
                models_used_list = models_to_try[:model_index + 1]
                
                # Debug: Log final result summary
                self.logger.info("+"*80)
                self.logger.info("DEBUG: FINAL PROCESSING RESULT")
                self.logger.info("+"*80)
                self.logger.info(f"Model used: {model_name}")
                self.logger.info(f"Models tried: {models_used_list}")
                self.logger.info(f"Similarity score: {similarity_score:.4f}")
                self.logger.info(f"Quality control passed: {quality_passed}")
                self.logger.info(f"Human intervention required: {human_intervention}")
                self.logger.info(f"Processing time: {processing_time:.2f}s")
                self.logger.info("+"*80)
                
                return ProcessingResult(
                    success=True,
                    structured_data=structured_data,
                    model_used=model_name,
                    models_used=models_used_list,
                    processing_time=processing_time,
                    tokens_used=tokens_used,
                    text_similarity_score=similarity_score,
                    content_diff=content_diff,
                    quality_control_passed=quality_passed,
                    human_intervention_required=human_intervention
                )
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Model {model_name} failed: {e}")
                
                # If this is the last model, return failure
                if model_index == len(models_to_try) - 1:
                    break
                
                # Wait before trying next model
                await asyncio.sleep(2)
        
        # All models failed
        processing_time = time.time() - start_time
        return ProcessingResult(
            success=False,
            error_message=last_error or "All models failed",
            processing_time=processing_time
        )
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for norm structuring"""
        return """
Eres un experto en análisis de documentos legales argentinos. Tu tarea es transformar normas legales (leyes, decretos, resoluciones) en un objeto JSON con la siguiente estructura:

ESTRUCTURA JSON:
{
  "preamble": "Texto completo de la sección inicial (ministerio, decreto número, título, fecha, expediente), hasta el inicio de los artículos",
  "articles": [
    {
      "number": "Número del artículo (como entero en secuencia corregida)",
      "body": "Contenido del artículo sin incluir la palabra 'Artículo' ni el número"
    }
  ],
  "postamble": "Texto posterior a los artículos (disposiciones transitorias, anexos, cierres)",
  "short_document": "Texto completo cuando el documento no contiene secciones de preámbulo, artículos ni conclusiones, sino solo un cuerpo principal breve",
  "firms": "Firmas y nombres de funcionarios al final del documento",
  "references": [
    {
      "documentType": "Tipo de norma referenciada (ej: LEY, DECRETO, RESOLUCIÓN)",
      "number": "Número de la norma referenciada",
      "articles": [
        {
          "number": "Número del artículo referido",
          "body": "Texto del artículo si aparece citado"
        }
      ]
    }
  ]
}

INSTRUCCIONES:
1. **Corrección OCR**: Corrige errores de ortografía, puntuación y numeración producidos por digitalización.
2. **Numeración de artículos**: Si hay errores en la secuencia (ej: 1,1,3,4), corrige para que quede consecutiva (1,2,3,4). No alteres la numeración cuando se cite otra norma.
3. **Mantén el contenido original**: No elimines información, solo corrige errores obvios de digitalización.
4. **Campos vacíos**: Si una sección no existe, coloca string vacío "" (no null, no omitir el campo).
5. **Texto completo**: Todo el contenido debe quedar representado en los campos adecuados.
6. **Formato de salida**: Devuelve exclusivamente el JSON válido, sin texto adicional ni explicaciones.

""" 