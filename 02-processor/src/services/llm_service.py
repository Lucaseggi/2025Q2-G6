"""LLM service implementation"""

import logging
import json
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Add src to path for interfaces
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from interfaces.llm_service_interface import LLMServiceInterface, ProcessingResult as InterfaceProcessingResult

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


class LLMService(LLMServiceInterface):
    """LLM service for legal document processing with model escalation"""

    def __init__(self, config):
        self.config = config
        self.current_api_key_index = 0
        self.logger = logging.getLogger(__name__)

        if not self.config.gemini.api_keys:
            raise ValueError("No Gemini API keys configured")

        # Initialize with first API key
        genai.configure(api_key=self.config.gemini.api_keys[0])

    def _load_prompt(self, prompt_name: str) -> str:
        """Helper method to load prompt from file"""
        try:
            with open(f'/app/prompts/{prompt_name}.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load {prompt_name} prompt: {e}")
            raise Exception(f"Could not load {prompt_name} prompt: {e}")

    def get_quality_control_prompt(self) -> str:
        """Get prompt for quality control assessment"""
        return self._load_prompt('quality_control_prompt')

    def get_system_prompt(self) -> str:
        """Get the system prompt for norm structuring"""
        return self._load_prompt('system_prompt')

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
            response = _make_api_call()

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
            structured_data = self._parse_json_response(response.text)

            if not structured_data:
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
                tokens_used = 0

            return ProcessingResult(
                success=True,
                structured_data=structured_data,
                model_used=model_name,
                tokens_used=tokens_used
            )

        except Exception as e:
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
            return None

    def _rotate_api_key(self):
        """Rotate to next API key"""
        if len(self.config.gemini.api_keys) > 1:
            self.current_api_key_index = (self.current_api_key_index + 1) % len(self.config.gemini.api_keys)
            genai.configure(api_key=self.config.gemini.api_keys[self.current_api_key_index])

    def process_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> InterfaceProcessingResult:
        """Process text through LLM"""
        start_time = time.time()
        models_used = []

        # Try each model in escalation chain
        for model_index, model_name in enumerate(self.config.gemini.models):
            try:
                result = self._call_gemini_with_retries_sync(model_name, text, self.get_system_prompt())
                models_used.append(model_name)

                if result.success:
                    result.models_used = models_used
                    result.processing_time = time.time() - start_time

                    # Return successful result as interface ProcessingResult
                    return InterfaceProcessingResult(
                        success=True,
                        structured_data=result.structured_data,
                        model_used=model_name,
                        processing_time=result.processing_time,
                        tokens_used=result.tokens_used
                    )

            except Exception as e:
                if model_index < len(self.config.gemini.models) - 1:
                    continue

        # All models failed
        return InterfaceProcessingResult(
            success=False,
            error_message="All models failed to process the text",
            processing_time=time.time() - start_time
        )

    def is_available(self) -> bool:
        """Check if LLM service is available"""
        try:
            return bool(self.config.gemini.api_keys)
        except:
            return False