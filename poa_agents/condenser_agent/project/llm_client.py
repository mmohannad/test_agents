"""OpenAI LLM client for the Condenser Agent."""
import os
from typing import Optional

from openai import AsyncOpenAI
from agentex.lib.utils.logging import make_logger

logger = make_logger(__name__)


class CondenserLLMClient:
    """OpenAI client for generating Legal Briefs."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")

        logger.info(f"CondenserLLMClient - Model: {self.model}")
        logger.info(f"CondenserLLMClient - API Key present: {bool(api_key)}")

        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment variables")

        self.client = AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """
        Send a chat message and return the response.

        Args:
            user_message: The user's message
            system_message: Optional system message
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            The assistant's response text
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        logger.debug(f"Making LLM call - model: {self.model}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            logger.debug(f"LLM response received: {len(content)} characters")

            return content or ""

        except Exception as e:
            logger.error(f"LLM API request failed: {e}")
            raise

    async def close(self):
        """Close the client connection."""
        await self.client.close()
