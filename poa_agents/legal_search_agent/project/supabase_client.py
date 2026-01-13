"""Supabase client for the Legal Search Agent."""
import os
from typing import Optional
from datetime import datetime

from supabase import create_client, Client
from agentex.lib.utils.logging import make_logger

logger = make_logger(__name__)


class LegalSearchSupabaseClient:
    """Client for legal article search and result storage."""

    def __init__(self):
        """Initialize the Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set"
            )

        logger.info(f"Initializing Supabase client - URL: {supabase_url}")
        self.client: Client = create_client(supabase_url, supabase_key)

    def get_legal_brief(self, application_id: str) -> Optional[dict]:
        """
        Get the Legal Brief for an application.

        Args:
            application_id: The application UUID

        Returns:
            Legal Brief row or None
        """
        try:
            response = (
                self.client.table("legal_briefs")
                .select("*")
                .eq("application_id", application_id)
                .order("generated_at", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get legal brief: {e}")
            return None

    def semantic_search(
        self,
        query_embedding: list[float],
        language: str = "english",
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> list[dict]:
        """
        Perform semantic search on articles.

        Args:
            query_embedding: The embedding vector (1536 dimensions)
            language: Language for search (english or arabic)
            limit: Maximum results
            similarity_threshold: Minimum similarity

        Returns:
            List of articles with similarity scores
        """
        logger.info(f"Semantic search - language: {language}, limit: {limit}")

        try:
            response = self.client.rpc(
                "match_articles",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": float(similarity_threshold),
                    "match_count": int(limit),
                    "language": language,
                }
            ).execute()

            results = response.data if response.data else []
            logger.info(f"Found {len(results)} articles")

            # If no results, try with lower threshold
            if len(results) == 0 and similarity_threshold > 0.2:
                logger.info("Retrying with lower threshold (0.2)...")
                response = self.client.rpc(
                    "match_articles",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.2,
                        "match_count": int(limit),
                        "language": language,
                    }
                ).execute()
                results = response.data if response.data else []
                logger.info(f"Found {len(results)} articles with lower threshold")

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Try fallback to get some articles
            return self._fallback_search(limit)

    def _fallback_search(self, limit: int) -> list[dict]:
        """Fallback search if semantic search fails."""
        logger.warning("Using fallback text search")
        try:
            response = (
                self.client.table("articles")
                .select("article_number, hierarchy_path, text_arabic, text_english")
                .eq("is_active", True)
                .limit(limit)
                .execute()
            )
            results = response.data if response.data else []
            # Add fake similarity for consistency
            for r in results:
                r["similarity"] = 0.5
            return results
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []

    def get_article_by_number(self, article_number: int) -> Optional[dict]:
        """
        Get a specific article by number.

        Args:
            article_number: The article number

        Returns:
            Article dict or None
        """
        try:
            response = (
                self.client.table("articles")
                .select("*")
                .eq("article_number", article_number)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Failed to get article {article_number}: {e}")
            return None

    def save_legal_opinion(
        self,
        application_id: str,
        opinion: dict,
        legal_brief_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        Save a legal opinion to the database.

        Args:
            application_id: The application UUID
            opinion: The legal opinion data
            legal_brief_id: Optional Legal Brief ID

        Returns:
            Saved row or None
        """
        try:
            row = {
                "application_id": application_id,
                "legal_brief_id": legal_brief_id,
                "finding": opinion.get("overall_finding", "INCONCLUSIVE"),
                "confidence_score": opinion.get("confidence_score", 0),
                "confidence_level": opinion.get("confidence_level", "LOW"),
                "summary_ar": opinion.get("opinion_summary_ar"),
                "summary_en": opinion.get("opinion_summary_en"),
                "full_analysis": opinion,
                "concerns": opinion.get("concerns", []),
                "recommendations": opinion.get("recommendations", []),
                "legal_citations": opinion.get("all_citations", []),
                "grounding_score": opinion.get("grounding_score", 0),
                "retrieval_coverage": opinion.get("retrieval_coverage", 0),
                "has_contradictions": False,
                "needs_escalation": opinion.get("decision_bucket") == "needs_review",
                "created_at": datetime.now().isoformat()
            }

            response = (
                self.client.table("legal_opinions")
                .insert(row)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Failed to save legal opinion: {e}")
            return None

    def save_analysis_session(
        self,
        application_id: str,
        legal_brief_id: str,
        status: str = "completed"
    ) -> Optional[dict]:
        """
        Save a legal analysis session.

        Args:
            application_id: The application UUID
            legal_brief_id: The Legal Brief ID
            status: Session status

        Returns:
            Saved row or None
        """
        try:
            row = {
                "application_id": application_id,
                "legal_brief_id": legal_brief_id,
                "status": status,
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat() if status == "completed" else None
            }

            response = (
                self.client.table("legal_analysis_sessions")
                .insert(row)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Failed to save analysis session: {e}")
            return None
