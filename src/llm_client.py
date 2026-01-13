"""
LLM Client

OpenAI-compatible client wrapper for resume generation.
Supports any provider with OpenAI-compatible API by configuring base_url.

Author: InternTrack
Version: 1.0
"""

import logging
from typing import Optional
from openai import OpenAI
import os

try:
    from .config import settings
except ImportError:
    # Fallback for when running independently
    class Settings:
        LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'http://localhost:4141/')
        LLM_API_KEY = os.getenv('LLM_API_KEY')
        LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o')
    settings = Settings()

logger = logging.getLogger(__name__)


class LLMClient:
    """
    OpenAI-compatible LLM client.

    Configurable via environment variables:
    - LLM_BASE_URL: API endpoint (default: OpenAI)
    - LLM_API_KEY: API key
    - LLM_MODEL: Model to use (default: gpt-4o)

    Usage:
        client = LLMClient()
        response = client.generate("You are helpful.", "Hello!")

    With custom provider (e.g., Ollama):
        client = LLMClient(base_url="http://localhost:11434/v1", api_key="ollama")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize LLM client.

        Args:
            base_url: API base URL (default from settings.LLM_BASE_URL)
            api_key: API key (default from settings.LLM_API_KEY)
            model: Model name (default from settings.LLM_MODEL)
        """
        self.base_url = base_url or getattr(settings, 'LLM_BASE_URL', 'https://api.openai.com/v1')
        self.api_key = api_key or getattr(settings, 'LLM_API_KEY', None)
        self.model = model or getattr(settings, 'LLM_MODEL', 'gpt-4o')

        if not self.api_key:
             # Allow initialization without API key for testing/mocking purposes,
             # but warn heavily. Some local providers (Ollama) might not strictly require it,
             # but OpenAI SDK usually expects a non-empty string.
             logger.warning("LLM_API_KEY is not set. LLM calls may fail.")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "dummy-key-for-local" # validation might fail if empty
        )

        logger.info(f"LLM client initialized: {self.base_url}, model: {self.model}")
    # TODO: here we are trusting the LLM to return valid JSON, a more robust implementation 
    # would invove using the structure output api , and validate on top with pydantic
    # for ref check out this :https://platform.openai.com/docs/guides/structured-outputs , 
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System message setting context/role
            user_prompt: User message with the actual request
            temperature: Randomness (0-1, lower = more deterministic)
            max_tokens: Maximum response length

        Returns:
            str: The LLM's response text

        Raises:
            Exception: If LLM call fails
        """
        try:
            logger.debug(f"Calling LLM with {len(user_prompt)} char prompt")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            logger.debug(f"LLM response received: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    # NOTE: keeping tyhis here until the structred output solution is implemented
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3
    ) -> str:
        """
        Generate JSON response from the LLM.

        Uses lower temperature for more deterministic/consistent output.

        Args:
            system_prompt: System message setting context/role
            user_prompt: User message with the actual request
            temperature: Randomness (default 0.3 for consistency)

        Returns:
            str: JSON string from LLM (may need cleaning)
        """
        return self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=4000
        )
