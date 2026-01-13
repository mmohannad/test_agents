"""Supabase client for semantic search over legal articles."""
import os
from typing import Optional

from supabase import create_client, Client
from agentex.lib.utils.logging import make_logger

logger = make_logger(__name__)


class SearchClient:
    """Client for performing semantic search on Supabase articles table."""

    def __init__(self):
        """Initialize the Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"
            )

        logger.info(f"Initializing Supabase client - URL: {supabase_url}")
        self.client: Client = create_client(supabase_url, supabase_key)
        # Table name is lowercase: "articles"
        self.table_name = "articles"

    def semantic_search(
        self,
        query_embedding: list[float],
        language: str = "english",
        limit: int = 5,
        similarity_threshold: float = 0.5,
    ) -> list[dict]:
        """
        Perform semantic search on articles using vector similarity.

        Args:
            query_embedding: The embedding vector of the search query (1536 dimensions)
            language: Language to search in ("english" or "arabic")
            limit: Maximum number of results to return
            similarity_threshold: Minimum cosine similarity threshold (0-1)

        Returns:
            List of article dictionaries with their similarity scores
        """
        # Determine which embedding column to use
        embedding_column = "embedding" if language == "english" else "arabic_embedding"

        logger.info(
            f"Performing semantic search - language: {language}, limit: {limit}, "
            f"threshold: {similarity_threshold}"
        )

        try:
            # Use Supabase RPC for vector similarity search
            # Note: We use a database function because pgvector operations (<=>) must run
            # on the database side for performance. The database has optimized IVFFlat
            # indexes that make vector similarity search fast. We can't efficiently do
            # this from Python without pulling all 1148+ embeddings.
            
            logger.debug(f"Calling match_articles RPC with embedding length: {len(query_embedding)}")
            
            response = (
                self.client.rpc(
                    "match_articles",
                    {
                        "query_embedding": query_embedding,  # List of floats, Supabase converts to vector
                        "match_threshold": float(similarity_threshold),
                        "match_count": int(limit),
                        "language": language,
                    },
                )
                .execute()
            )

            results = response.data if response.data else []
            logger.info(f"Found {len(results)} articles matching the query")
            
            # If no results, try with a lower threshold
            if len(results) == 0 and similarity_threshold > 0.3:
                logger.info(f"No results with threshold {similarity_threshold}, trying 0.3...")
                response = (
                    self.client.rpc(
                        "match_articles",
                        {
                            "query_embedding": query_embedding,
                            "match_threshold": 0.3,
                            "match_count": int(limit),
                            "language": language,
                        },
                    )
                    .execute()
                )
                results = response.data if response.data else []
                logger.info(f"Found {len(results)} articles with lower threshold")
            
            return results

        except Exception as e:
            # Log the full error for debugging
            logger.error(f"RPC function 'match_articles' failed: {e}", exc_info=True)
            logger.warning("Trying alternative search method...")
            return self._direct_vector_search(
                query_embedding, embedding_column, limit, similarity_threshold
            )

    def _direct_vector_search(
        self,
        query_embedding: list[float],
        embedding_column: str,
        limit: int,
        similarity_threshold: float,
    ) -> list[dict]:
        """
        Direct vector search using Supabase Postgres functions.
        This is a fallback if RPC function doesn't exist.
        
        Note: Vector similarity search requires a database function since pgvector
        operators cannot be used directly through Supabase's query builder.
        See README for SQL to create the match_articles function.
        """
        # Since pgvector operators need SQL, we can't use the query builder directly
        # The user must create the match_articles RPC function
        logger.error(
            "Vector search requires the 'match_articles' database function. "
            "Please run the SQL provided in the README to create this function."
        )
        # Return empty results so the agent can still respond (without context)
        return []

    def _fallback_text_search(self, limit: int) -> list[dict]:
        """Fallback to simple text-based search if vector search fails."""
        logger.warning("Using fallback text search")
        try:
            response = (
                self.client.table(self.table_name)
                .select("article_number, hierarchy_path, text_arabic, text_english")
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            return []

    def get_article_by_number(self, article_number: int) -> Optional[dict]:
        """
        Retrieve a specific article by its number.

        Args:
            article_number: The article number to retrieve

        Returns:
            Article dictionary or None if not found
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("article_number", article_number)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Failed to retrieve article {article_number}: {e}")
            return None

