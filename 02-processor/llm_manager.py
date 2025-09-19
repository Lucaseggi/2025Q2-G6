"""LLM management with model escalation and quality control"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import ProcessingConfig
from response_verifier import ResponseVerifier

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


class LLMManager:
    """LLM manager for legal document processing with model escalation"""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.current_api_key_index = 0
        self.logger = logging.getLogger(__name__)
        self.verifier = ResponseVerifier(diff_threshold=config.gemini.diff_threshold)

        if not self.config.gemini.api_keys:
            raise ValueError("No Gemini API keys configured")

        # Initialize with first API key
        genai.configure(api_key=self.config.gemini.api_keys[0])


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
                json_valid, json_error = self.verifier.validate_json_structure(structured_data)

                if not json_valid:
                    return False, True, f"JSON structure validation failed: {json_error}"

                self.logger.info("JSON structure validation passed")

            except json.JSONDecodeError as e:
                return False, True, f"Invalid JSON format: {str(e)}"

            # Step 2: Similarity Check
            similarity = self.verifier.calculate_text_similarity(original_text, structured_result)
            if similarity == 1.0:
                return True, False, f"Perfect similarity ({similarity:.3f}) - content perfectly preserved"

            # If similarity is very high, approve directly (but after JSON validation)
            if similarity >= 0.9:
                return True, False, f"Very high similarity ({similarity:.3f}) - direct approval"

            # If similarity is very low, require human intervention
            if similarity < 0.85:
                return False, True, f"Low similarity ({similarity:.3f}) - major changes detected"

            # Generate diff for analysis
            content_diff = self.verifier.generate_content_diff(original_text, structured_result)

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
                    json_valid, json_error = self.verifier.validate_json_structure(result.structured_data)
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
                    similarity = self.verifier.calculate_text_similarity(text, json.dumps(result.structured_data))
                    result.text_similarity_score = similarity
                    result.models_used = models_used
                    result.processing_time = time.time() - start_time

                    logger.info(f"SIMILARITY SCORE: {similarity:.4f}")

                    # Generate content diff
                    result.content_diff = self.verifier.generate_content_diff(text, json.dumps(result.structured_data))
                    
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