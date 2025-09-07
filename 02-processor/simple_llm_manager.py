"""LLM management with model escalation and quality control"""

import logging
import json
import time
import difflib
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import ProcessingConfig

logger = logging.getLogger(__name__)


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
    json_validation_passed: bool = False
    json_validation_error: Optional[str] = None


class SimpleLLMManager:
    """Simplified LLM manager for legal document processing with model escalation"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.current_api_key_index = 0
        self.logger = logging.getLogger(__name__)
        
        if not self.config.gemini.api_keys:
            raise ValueError("No Gemini API keys configured")
            
        # Initialize with first API key
        genai.configure(api_key=self.config.gemini.api_keys[0])

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

    def _validate_json_structure(self, structured_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate JSON structure against expected schema"""
        try:
            # Required fields according to the prompt
            required_fields = ["preamble", "articles", "postamble", "short_document", "firms", "references"]
            
            # Check all required fields exist
            for field in required_fields:
                if field not in structured_data:
                    return False, f"Missing required field: {field}"
            
            # Validate articles structure if present
            articles = structured_data.get("articles", [])
            if articles and isinstance(articles, list):
                for i, article in enumerate(articles):
                    if not isinstance(article, dict):
                        return False, f"Article {i} is not a dictionary"
                    if "number" not in article:
                        return False, f"Article {i} missing 'number' field"
                    if "body" not in article:
                        return False, f"Article {i} missing 'body' field"
                    # Validate number is integer or string convertible to int
                    try:
                        int(article["number"])
                    except (ValueError, TypeError):
                        return False, f"Article {i} has invalid number format: {article.get('number')}"
            
            # Validate references structure if present
            references = structured_data.get("references", [])
            if references and isinstance(references, list):
                for i, ref in enumerate(references):
                    if not isinstance(ref, dict):
                        return False, f"Reference {i} is not a dictionary"
                    if "documentType" not in ref:
                        return False, f"Reference {i} missing 'documentType' field"
                    if "number" not in ref:
                        return False, f"Reference {i} missing 'number' field"
                    if "articles" not in ref:
                        return False, f"Reference {i} missing 'articles' field"
                    
                    # Validate reference articles
                    ref_articles = ref.get("articles", [])
                    if ref_articles and isinstance(ref_articles, list):
                        for j, ref_article in enumerate(ref_articles):
                            if not isinstance(ref_article, dict):
                                return False, f"Reference {i} article {j} is not a dictionary"
                            if "number" not in ref_article:
                                return False, f"Reference {i} article {j} missing 'number' field"
                            if "body" not in ref_article:
                                return False, f"Reference {i} article {j} missing 'body' field"
            
            # Check string fields are actually strings
            string_fields = ["preamble", "postamble", "short_document", "firms"]
            for field in string_fields:
                value = structured_data.get(field)
                if value is not None and not isinstance(value, str):
                    return False, f"Field '{field}' must be a string, got {type(value)}"
            
            return True, "JSON structure validation passed"
            
        except Exception as e:
            return False, f"JSON validation error: {str(e)}"

    def _perform_quality_control(self, original_text: str, structured_result: str) -> Tuple[bool, bool, str]:
        """Perform quality control using similarity score, JSON validation, and LLM assessment"""
        try:
            # Step 1: JSON Structure Validation
            try:
                clean_json = structured_result.strip()
                if clean_json.startswith('```json'):
                    clean_json = clean_json[7:]
                if clean_json.endswith('```'):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                structured_data = json.loads(clean_json)
                json_valid, json_error = self._validate_json_structure(structured_data)
                
                if not json_valid:
                    return False, True, f"JSON structure validation failed: {json_error}"
                
                self.logger.info("JSON structure validation passed")
                
            except json.JSONDecodeError as e:
                return False, True, f"Invalid JSON format: {str(e)}"
            
            # Step 2: Similarity Check
            similarity = self._calculate_text_similarity(original_text, structured_result)
            if similarity == 1.0:
                return True, False, f"Perfect similarity ({similarity:.3f}) - content perfectly preserved"
            
            # If similarity is very high, approve directly (but after JSON validation)
            if similarity >= 0.9:
                return True, False, f"Very high similarity ({similarity:.3f}) - direct approval"
            
            # If similarity is very low, require human intervention
            if similarity < 0.85:
                return False, True, f"Low similarity ({similarity:.3f}) - major changes detected"
            
            # Generate diff for analysis
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
            response = self._call_gemini_with_retries_sync(qc_model, qc_prompt, self.get_quality_control_prompt())
            
            if not response.success:
                return False, True, "Quality control API call failed"
            
            # Parse quality control response
            try:
                qc_result = json.loads(response.structured_data.strip())
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
        """Get prompt for quality control assessment"""
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

    def _call_gemini_with_retries_sync(self, model_name: str, text: str, system_prompt: str) -> ProcessingResult:
        """Call Gemini API with retries synchronously"""
        
        @retry(
            stop=stop_after_attempt(self.config.gemini.max_retries),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((Exception,))
        )
        def _make_api_call():
            # Rotate API key if needed
            self._rotate_api_key()
            
            # Create the model with system instruction
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )
            
            # Make the API call
            response = model.generate_content(
                text,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config.gemini.max_output_tokens,
                    temperature=0.1,
                    top_p=0.8,
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            
            return response
        
        try:
            logger.info(f"    Making API call to {model_name}...")
            response = _make_api_call()
            logger.info(f"    API call successful, response length: {len(response.text) if response.text else 0}")
            
            # For quality control calls, return the raw text
            if "analiza el siguiente diff" in text.lower():
                tokens_used = 0
                try:
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                        if hasattr(response.usage_metadata, 'totalTokenCount'):
                            tokens_used = response.usage_metadata.totalTokenCount
                        elif hasattr(response.usage_metadata, 'total_token_count'):
                            tokens_used = response.usage_metadata.total_token_count
                except:
                    tokens_used = 0
                    
                return ProcessingResult(
                    success=True,
                    structured_data=response.text,
                    model_used=model_name,
                    tokens_used=tokens_used
                )
            
            # Parse JSON response for structuring calls
            logger.info(f"    Parsing JSON response...")
            structured_data = self._parse_json_response(response.text)
            
            if not structured_data:
                logger.error(f"    JSON parsing failed - raw response: {response.text[:200]}...")
                return ProcessingResult(
                    success=False,
                    error_message="Failed to parse JSON from API response",
                    model_used=model_name
                )
            
            # Try to get token usage safely
            tokens_used = 0
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    # Try different possible field names
                    if hasattr(response.usage_metadata, 'totalTokenCount'):
                        tokens_used = response.usage_metadata.totalTokenCount
                    elif hasattr(response.usage_metadata, 'total_token_count'):
                        tokens_used = response.usage_metadata.total_token_count
                    else:
                        tokens_used = 0
            except Exception as e:
                logger.debug(f"Could not get token usage: {e}")
                tokens_used = 0
            
            return ProcessingResult(
                success=True,
                structured_data=structured_data,
                model_used=model_name,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"    Exception in _call_gemini_with_retries_sync: {type(e).__name__}: {str(e)}")
            return ProcessingResult(
                success=False,
                error_message=str(e),
                model_used=model_name
            )

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from API response"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Try parsing the entire response as JSON
                return json.loads(response_text)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return None

    def _rotate_api_key(self):
        """Rotate to next API key"""
        if len(self.config.gemini.api_keys) > 1:
            self.current_api_key_index = (self.current_api_key_index + 1) % len(self.config.gemini.api_keys)
            genai.configure(api_key=self.config.gemini.api_keys[self.current_api_key_index])
            logger.info(f"Rotated to API key {self.current_api_key_index + 1}")

    def process_text_with_escalation(self, text: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """Process text through LLM with model escalation"""
        start_time = time.time()
        models_used = []
        
        # DEBUG: Log the input text for debugging
        logger.info("="*80)
        logger.info("DEBUG: INPUT TEXT TO LLM PROCESSING")
        logger.info("="*80)
        logger.info(f"Text length: {len(text)} characters")
        logger.info(f"Text preview (first 500 chars):")
        logger.info(f"{text[:500]}...")
        if len(text) > 500:
            logger.info(f"Text preview (last 200 chars):")
            logger.info(f"...{text[-200:]}")
        logger.info("="*80)
        
        # Try each model in escalation chain
        for model_index, model_name in enumerate(self.config.gemini.models):
            try:
                logger.info(f"ATTEMPTING MODEL {model_index + 1}/{len(self.config.gemini.models)}: {model_name}")
                
                result = self._call_gemini_with_retries_sync(model_name, text, self.get_system_prompt())
                models_used.append(model_name)
                
                # DEBUG: Log the result status
                logger.info(f"   API call result: Success={result.success}")
                if not result.success:
                    logger.error(f"   API call failed: {result.error_message}")
                else:
                    logger.info(f"   Tokens used: {result.tokens_used}")
                
                if result.success:
                    # DEBUG: Log the raw LLM output
                    logger.info(f"MODEL {model_name} - API CALL SUCCESSFUL")
                    logger.info("-"*60)
                    logger.info("DEBUG: RAW LLM OUTPUT:")
                    logger.info("-"*60)
                    raw_output = json.dumps(result.structured_data, indent=2)[:1000]
                    logger.info(f"{raw_output}...")
                    logger.info("-"*60)
                    
                    # Validate JSON structure first
                    json_valid, json_error = self._validate_json_structure(result.structured_data)
                    result.json_validation_passed = json_valid
                    result.json_validation_error = json_error if not json_valid else None
                    
                    logger.info(f"JSON VALIDATION: {'PASSED' if json_valid else 'FAILED'}")
                    if not json_valid:
                        logger.error(f"JSON validation error: {json_error}")
                    
                    # If JSON validation fails and we're not on the last model, escalate immediately
                    if not json_valid and model_name != self.config.gemini.models[-1]:
                        logger.warning(f"ESCALATING: JSON validation failed with {model_name}")
                        logger.warning(f"   Reason: {json_error}")
                        logger.warning(f"   Moving to next model...")
                        result.models_used = models_used
                        result.processing_time = time.time() - start_time
                        continue
                    
                    # Calculate similarity for quality control (only if JSON is valid or on last model)
                    similarity = self._calculate_text_similarity(text, json.dumps(result.structured_data))
                    result.text_similarity_score = similarity
                    result.models_used = models_used
                    result.processing_time = time.time() - start_time
                    
                    logger.info(f"SIMILARITY SCORE: {similarity:.4f}")
                    
                    # Generate content diff
                    result.content_diff = self._generate_content_diff(text, json.dumps(result.structured_data))
                    
                    # Perform quality control (includes JSON validation)
                    quality_passed, human_intervention, qc_reason = self._perform_quality_control(
                        text, json.dumps(result.structured_data)
                    )
                    result.quality_control_passed = quality_passed
                    result.human_intervention_required = human_intervention
                    
                    logger.info(f"QUALITY CONTROL: {'PASSED' if quality_passed else 'FAILED'}")
                    logger.info(f"HUMAN INTERVENTION: {'REQUIRED' if human_intervention else 'NOT NEEDED'}")
                    if not quality_passed or human_intervention:
                        logger.info(f"   Reason: {qc_reason}")
                    
                    # Check if we should return this result or escalate
                    # Return if: (JSON valid AND quality passed) OR we're on the last model
                    if (json_valid and quality_passed) or model_name == self.config.gemini.models[-1]:
                        if json_valid and quality_passed:
                            logger.info(f"SUCCESS WITH {model_name}: All checks passed!")
                        else:
                            logger.warning(f"FINAL MODEL {model_name}: Returning despite issues")
                            if not json_valid:
                                logger.warning(f"   - JSON validation failed: {json_error}")
                            if not quality_passed:
                                logger.warning(f"   - Quality control failed: {qc_reason}")
                        return result
                    else:
                        # Need to escalate to next model
                        escalation_reasons = []
                        if not json_valid:
                            escalation_reasons.append(f"JSON validation failed: {json_error}")
                        if not quality_passed:
                            escalation_reasons.append(f"Quality control failed: {qc_reason}")
                        
                        logger.warning(f"ESCALATING FROM {model_name}:")
                        for reason in escalation_reasons:
                            logger.warning(f"   - {reason}")
                        continue
                        
            except Exception as e:
                logger.error(f"MODEL {model_name} - API CALL FAILED")
                logger.error(f"   Error: {str(e)}")
                logger.error(f"   Exception type: {type(e).__name__}")
                if model_index < len(self.config.gemini.models) - 1:
                    logger.info(f"   Moving to next model...")
                continue
        
        # All models failed
        return ProcessingResult(
            success=False,
            error_message="All models failed to process the text",
            models_used=models_used,
            processing_time=time.time() - start_time
        )