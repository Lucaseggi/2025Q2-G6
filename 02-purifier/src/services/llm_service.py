import logging
import time
from typing import Optional
from dataclasses import dataclass

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of LLM orthography fix"""
    success: bool
    fixed_text: Optional[str] = None
    model_used: str = ""
    tokens_used: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None


class LLMService:
    """LLM service for orthography and numbering fixes"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        if not self.settings.gemini.api_key:
            raise ValueError("No Gemini API key configured")

        genai.configure(api_key=self.settings.gemini.api_key)

    def _load_prompt(self) -> str:
        """Load orthography fix prompt from file"""
        try:
            with open('/app/prompts/orthography_fix_prompt.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load orthography fix prompt: {e}")
            raise Exception(f"Could not load orthography fix prompt: {e}")

    def _rotate_api_key(self):
        """No-op: API key rotation removed (single key only)"""
        pass

    def _call_gemini_with_retries(self, model_name: str, text: str, system_prompt: str) -> FixResult:
        """Call Gemini API with retries"""

        @retry(
            stop=stop_after_attempt(self.settings.gemini.max_retries),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type((Exception,))
        )
        def _make_api_call():
            self._rotate_api_key()

            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )

            response = model.generate_content(
                text,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.settings.gemini.max_output_tokens,
                    temperature=0.1,
                    top_p=0.8,
                )
            )

            if not response.text:
                raise ValueError("Empty response from Gemini API")

            return response

        try:
            response = _make_api_call()

            tokens_used = 0
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    if hasattr(response.usage_metadata, 'totalTokenCount'):
                        tokens_used = response.usage_metadata.totalTokenCount
                    elif hasattr(response.usage_metadata, 'total_token_count'):
                        tokens_used = response.usage_metadata.total_token_count
            except:
                tokens_used = 0

            return FixResult(
                success=True,
                fixed_text=response.text,
                model_used=model_name,
                tokens_used=tokens_used
            )

        except Exception as e:
            return FixResult(
                success=False,
                error_message=str(e),
                model_used=model_name
            )

    def fix_orthography_and_numbering(self, text: str, infoleg_id: int) -> FixResult:
        """Fix orthography and numbering issues in text"""
        start_time = time.time()

        system_prompt = self._load_prompt()

        for model_name in self.settings.gemini.models:
            try:
                logger.info(f"Attempting orthography fix for {infoleg_id} with model {model_name}")
                result = self._call_gemini_with_retries(model_name, text, system_prompt)

                if result.success:
                    result.processing_time = time.time() - start_time
                    logger.info(f"Model {model_name} successfully fixed orthography for {infoleg_id}")
                    return result
                else:
                    logger.warning(f"Model {model_name} failed for {infoleg_id}: {result.error_message}")

            except Exception as e:
                logger.error(f"Model {model_name} failed for {infoleg_id}: {str(e)}")
                continue

        logger.error(f"All models failed to fix orthography for {infoleg_id}")
        return FixResult(
            success=False,
            error_message="All models failed to fix the text",
            processing_time=time.time() - start_time
        )

    def is_available(self) -> bool:
        """Check if LLM service is available"""
        try:
            return bool(self.settings.gemini.api_key)
        except:
            return False
