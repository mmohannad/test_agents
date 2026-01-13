"""OpenAI LLM client for the Legal Search Agent."""
import os
from typing import Optional

from openai import AsyncOpenAI
from agentex.lib.utils.logging import make_logger

logger = make_logger(__name__)


class LegalSearchLLMClient:
    """OpenAI client for legal research and synthesis."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        api_key = os.getenv("OPENAI_API_KEY")

        logger.info(f"LegalSearchLLMClient - Model: {self.model}")
        logger.info(f"LegalSearchLLMClient - Embedding Model: {self.embedding_model}")
        logger.info(f"LegalSearchLLMClient - Embedding Dimensions: {self.embedding_dimensions}")

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
            temperature: Sampling temperature
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
            logger.debug(f"LLM response: {len(content)} characters")

            return content or ""

        except Exception as e:
            logger.error(f"LLM API request failed: {e}")
            raise

    async def get_embedding(self, text: str, model: Optional[str] = None) -> list[float]:
        """
        Generate an embedding vector for text.

        Args:
            text: The text to embed
            model: Optional model override

        Returns:
            Embedding vector (1536 dimensions)
        """
        if model is None:
            model = self.embedding_model

        logger.debug(f"Generating embedding for: {text[:100]}...")

        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text,
                dimensions=self.embedding_dimensions,
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding: {len(embedding)} dimensions")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def close(self):
        """Close the client connection."""
        await self.client.close()
