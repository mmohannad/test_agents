"""ACP server for the search agent with Azure OpenAI integration."""
import os
from pathlib import Path
from typing import AsyncGenerator

import dotenv
from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.text_content import TextContent
from agentex.lib.utils.logging import make_logger

from project.llm_client import SimpleLLMClient
from project.search_client import SearchClient

logger = make_logger(__name__)

# Load .env file from the search_agent directory (parent of project/)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    dotenv.load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f".env file not found at {env_path}. Using system environment variables.")

# Initialize clients (will be created on first use)
_llm_client: SimpleLLMClient | None = None
_search_client: SearchClient | None = None


def get_llm_client() -> SimpleLLMClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = SimpleLLMClient()
    return _llm_client


def get_search_client() -> SearchClient:
    """Get or create the search client singleton."""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient()
    return _search_client


# Create an ACP server
acp = FastACP.create(
    acp_type="sync",
)


@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams
) -> TaskMessageContent | list[TaskMessageContent] | AsyncGenerator[TaskMessageUpdate, None]:
    """
    Handle incoming messages with semantic search over legal articles.
    
    Process:
    1. Extract user query
    2. Generate embedding for the query
    3. Search Supabase for relevant articles
    4. Use found articles as context
    5. Generate intelligent response with citations
    """
    # Extract user message from params
    user_message = params.content.content if params.content else ""
    
    if not user_message:
        return TextContent(
            author="agent",
            content="I didn't receive any message. Please try again.",
        )
    
    logger.info(f"Received message: {user_message[:100]}...")
    
    try:
        # Get clients
        llm_client = get_llm_client()
        search_client = get_search_client()
        
        # Step 1: Generate embedding for the user query
        logger.info("Generating embedding for query...")
        query_embedding = await llm_client.get_embedding(user_message)
        
        # Step 2: Perform semantic search (default to English, could be made configurable)
        # Run synchronous Supabase operations in a thread pool to avoid blocking
        import asyncio
        logger.info("Performing semantic search...")
        search_results = await asyncio.to_thread(
            search_client.semantic_search,
            query_embedding=query_embedding,
            language="english",  # Could detect language or make configurable
            limit=5,
            similarity_threshold=0.3,  # Lowered from 0.5 to get more results
        )
        
        # Step 3: Build context from search results
        context_parts = []
        if search_results:
            logger.info(f"Found {len(search_results)} relevant articles")
            context_parts.append("Relevant Legal Articles Found:\n")
            for idx, article in enumerate(search_results, 1):
                article_num = article.get("article_number", "N/A")
                text_english = article.get("text_english", "")
                text_arabic = article.get("text_arabic", "")
                similarity = article.get("similarity", 0)
                
                # Format article with similarity score
                article_text = f"\n[Article {article_num}]"
                if similarity > 0:
                    article_text += f" (Similarity: {similarity:.2%})"
                article_text += "\n"
                
                if text_english:
                    article_text += f"English: {text_english[:500]}"
                    if len(text_english) > 500:
                        article_text += "..."
                    article_text += "\n"
                
                if text_arabic:
                    article_text += f"Arabic: {text_arabic[:500]}"
                    if len(text_arabic) > 500:
                        article_text += "..."
                    article_text += "\n"
                
                context_parts.append(article_text)
        else:
            logger.warning("No relevant articles found")
            context_parts.append(
                "No relevant articles found in the database. "
                "Please ensure the 'match_articles' database function is created. "
                "See README for setup instructions.\n"
            )
        
        context = "\n".join(context_parts)
        
        # Step 4: Generate response using LLM with context
        system_message = (
            "You are a legal research assistant specializing in analyzing legal articles. "
            "When answering questions, use the provided legal articles as your primary source. "
            "Cite specific article numbers when referencing information. "
            "If the articles don't contain relevant information, say so clearly. "
            "Provide clear, accurate, and helpful responses based on the legal articles provided."
        )
        
        user_prompt = f"""User Question: {user_message}

{context}

Based on the above legal articles, please provide a comprehensive answer to the user's question. 
Include citations to specific article numbers when referencing information from the articles."""
        
        logger.info("Generating response with context...")
        response = await llm_client.chat(
            user_message=user_prompt,
            system_message=system_message,
        )
        
        logger.info(f"Generated response: {len(response)} characters")
        
        return TextContent(
            author="agent",
            content=response,
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return TextContent(
            author="agent",
            content=f"I encountered an error while processing your message: {str(e)}. Please try again.",
        )