"""
LLM Client wrapper for Azure OpenAI.
Shared across all POA agents.
"""

import os
from typing import Optional
from openai import AsyncAzureOpenAI


class LLMClient:
    """Async Azure OpenAI client wrapper."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: Optional[str] = None,
        model: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required")
        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required")
        
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
        )
    
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """Send a chat completion request."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format
        
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat completion request expecting JSON output."""
        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    
    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding
    
    async def close(self):
        """Close the client."""
        await self.client.close()


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the singleton LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

