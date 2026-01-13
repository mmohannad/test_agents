"""Simple Azure OpenAI LLM client for the search agent."""
import os
from typing import Optional

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
from agentex.lib.utils.logging import make_logger

logger = make_logger(__name__)


class SimpleLLMClient:
    """Simple Azure OpenAI client wrapper for chat completions."""

    def __init__(self):
        """Initialize the Azure OpenAI client with API key or Azure AD authentication."""
        # Load configuration from environment variables
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self.azure_endpoint = os.getenv(
            "AZURE_OPENAI_ENDPOINT", "https://azure-openai-com.openai.azure.com/"
        )
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        # Support both API key (for local dev) and Azure AD token (for production)
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        # Debug logging
        logger.info(f"SimpleLLMClient initialization - AZURE_OPENAI_ENDPOINT: {self.azure_endpoint}")
        logger.info(f"SimpleLLMClient initialization - AZURE_OPENAI_API_VERSION: {self.api_version}")
        logger.info(f"SimpleLLMClient initialization - LLM_MODEL: {self.model}")
        logger.info(f"SimpleLLMClient initialization - AZURE_OPENAI_API_KEY present: {bool(api_key)}")
        if api_key:
            logger.info(f"SimpleLLMClient initialization - API key starts with: {api_key[:20]}...")

        if api_key:
            # Use API key authentication (simpler for local development)
            logger.info("Using API key authentication for Azure OpenAI")
            self.client = AsyncAzureOpenAI(
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=api_key,
            )
        else:
            # Use Azure AD token provider (for production/managed identity)
            logger.info("Using Azure AD token authentication for Azure OpenAI")
            try:
                self.token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
                self.client = AsyncAzureOpenAI(
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint,
                    azure_ad_token_provider=self.token_provider,
                )
            except Exception as e:
                logger.error(
                    "Failed to initialize Azure AD authentication. "
                    "Set AZURE_OPENAI_API_KEY for API key authentication, "
                    "or configure Azure credentials for managed identity authentication. "
                    f"Error: {e}"
                )
                raise

    async def chat(self, user_message: str, system_message: Optional[str] = None) -> str:
        """
        Send a chat message to Azure OpenAI and return the response.

        Args:
            user_message: The user's message
            system_message: Optional system message to set the assistant's behavior

        Returns:
            The assistant's response text
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        logger.debug(f"Making Azure OpenAI API call - model: {self.model}, endpoint: {self.azure_endpoint}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
            content = response.choices[0].message.content
            logger.debug(f"Azure OpenAI response received: {len(content)} characters")
            return content or ""
        except Exception as e:
            logger.error(f"Azure OpenAI API request failed. Error: {e}")
            raise

    async def get_embedding(
        self, text: str, model: str = None
    ) -> list[float]:
        """
        Generate an embedding vector for the given text using Azure OpenAI.

        Args:
            text: The text to generate an embedding for
            model: The embedding model deployment name in Azure OpenAI
                   (defaults to EMBEDDING_MODEL env var or "text-embedding-3-small")

        Returns:
            A list of floats representing the embedding vector (1536 dimensions for ada-002)
        """
        # Use environment variable or default model name
        # Default to text-embedding-3-small (1536 dims) to match your schema
        if model is None:
            model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        logger.info(f"Generating embedding for text: {text[:100]}... using model: {model}")

        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def close(self):
        """Close the client connection."""
        await self.client.close()

