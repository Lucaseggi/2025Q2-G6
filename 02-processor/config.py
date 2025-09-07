"""Simplified configuration for processing service"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class GeminiConfig:
    """Gemini LLM configuration"""
    models: List[str]
    api_keys: List[str]
    rate_limit: int = 60  # requests per minute
    max_input_tokens: int = 1048576
    max_output_tokens: int = 8192
    max_retries: int = 3
    retry_delay: int = 1
    diff_threshold: float = 0.3  # threshold for model escalation


class ProcessingConfig:
    """Configuration for processing service"""
    
    def __init__(self):
        # Gemini LLM configuration
        self.gemini = GeminiConfig(
            models=[
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-1.5-pro",
                "gemini-2.5-pro"
            ],
            api_keys=self._get_api_keys(),
            rate_limit=60,
            max_retries=3,
            diff_threshold=0.3
        )
    
    def _get_api_keys(self) -> List[str]:
        """Get API keys from environment variables"""
        keys = []
        for i in range(1, 6):  # Check for up to 5 API keys
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                keys.append(key)
        
        # Fallback to single API key
        if not keys:
            key = os.getenv('GEMINI_API_KEY')
            if key:
                keys.append(key)
        
        return keys