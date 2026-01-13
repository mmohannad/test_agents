"""
Retriever Component - RAG search for relevant legal articles.
"""
import os
import asyncio
from typing import TYPE_CHECKING

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient
    from project.supabase_client import LegalSearchSupabaseClient

logger = make_logger(__name__)


class ArticleRetriever:
    """Retrieves relevant legal articles using semantic search (RAG)."""

    def __init__(
        self,
        llm_client: "LegalSearchLLMClient",
        supabase_client: "LegalSearchSupabaseClient"
    ):
        self.llm = llm_client
        self.supabase = supabase_client
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
        self.max_articles = int(os.getenv("MAX_ARTICLES_PER_ISSUE", "5"))

    async def search_for_issue(self, issue: dict) -> list[dict]:
        """
        Search for relevant articles for a legal issue using Arabic queries.

        Args:
            issue: A legal issue from the decomposer

        Returns:
            List of relevant articles with similarity scores
        """
        # Prefer Arabic queries for better semantic match with Arabic legal corpus
        search_queries = issue.get("search_queries_ar", [])
        if not search_queries:
            search_queries = issue.get("search_queries", [])
        if not search_queries:
            search_queries = [issue.get("primary_question", "")]

        all_articles = []

        # Search using each query (in Arabic, against Arabic embeddings)
        for query in search_queries:
            if not query:
                continue

            logger.info(f"Searching (Arabic): {query[:100]}...")

            try:
                # Generate embedding for the Arabic query
                embedding = await self.llm.get_embedding(query)

                # Search in Supabase using Arabic embeddings
                articles = await asyncio.to_thread(
                    self.supabase.semantic_search,
                    query_embedding=embedding,
                    language="arabic",  # Use Arabic embedding column
                    limit=self.max_articles,
                    similarity_threshold=self.similarity_threshold
                )

                for article in articles:
                    # Add the query that found this article
                    article["found_by_query"] = query
                    all_articles.append(article)

                logger.info(f"Found {len(articles)} articles for query")

            except Exception as e:
                logger.error(f"Search failed for query '{query[:50]}...': {e}")
                continue

        # Deduplicate by article number, keeping highest similarity
        article_map = {}
        for article in all_articles:
            art_num = article.get("article_number")
            existing = article_map.get(art_num)
            if not existing or article.get("similarity", 0) > existing.get("similarity", 0):
                article_map[art_num] = article

        # Sort by similarity (highest first)
        unique_articles = list(article_map.values())
        unique_articles.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        # Limit to max articles
        return unique_articles[:self.max_articles]

    async def search_direct(
        self,
        query: str,
        language: str = "english"
    ) -> list[dict]:
        """
        Direct search with a specific query.

        Args:
            query: The search query
            language: Language for search (english or arabic)

        Returns:
            List of relevant articles
        """
        try:
            embedding = await self.llm.get_embedding(query)

            articles = await asyncio.to_thread(
                self.supabase.semantic_search,
                query_embedding=embedding,
                language=language,
                limit=self.max_articles,
                similarity_threshold=self.similarity_threshold
            )

            return articles

        except Exception as e:
            logger.error(f"Direct search failed: {e}")
            return []

    async def get_article_by_number(self, article_number: int) -> dict | None:
        """
        Get a specific article by its number.

        Args:
            article_number: The article number

        Returns:
            Article dict or None
        """
        return await asyncio.to_thread(
            self.supabase.get_article_by_number,
            article_number
        )
