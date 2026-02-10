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
        Perform semantic search on poa_articles table.

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
                "match_poa_articles",
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
                    "match_poa_articles",
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
                self.client.table("poa_articles")
                .select("article_number, hierarchy_path, text_arabic, text_english, citation")
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

    def get_article_by_number(self, article_number: int, law_id: int | None = None) -> Optional[dict]:
        """
        Get a specific article by number.

        Args:
            article_number: The article number
            law_id: Optional law ID to disambiguate (same article number can exist in different laws)

        Returns:
            Article dict or None
        """
        try:
            query = (
                self.client.table("poa_articles")
                .select("*")
                .eq("article_number", article_number)
            )
            if law_id:
                query = query.eq("law_id", law_id)

            response = query.limit(1).execute()
            return response.data[0] if response.data else None
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

    def save_retrieval_artifact(
        self,
        artifact: "RetrievalEvalArtifact"
    ) -> Optional[dict]:
        """
        Save a retrieval evaluation artifact for analysis.

        Args:
            artifact: The RetrievalEvalArtifact dataclass

        Returns:
            Saved row or None
        """
        from project.models.retrieval_state import RetrievalEvalArtifact

        try:
            # Convert dataclass to dict for storage
            row = {
                "artifact_id": artifact.artifact_id,
                "application_id": artifact.application_id if artifact.application_id != "unknown" else None,
                "legal_brief": artifact.legal_brief,
                "decomposed_issues": artifact.decomposed_issues,
                "config": {
                    "hyde_enabled": artifact.config.hyde_enabled,
                    "hyde_num_hypotheticals": artifact.config.hyde_num_hypotheticals,
                    "max_iterations": artifact.config.max_iterations,
                    "max_articles": artifact.config.max_articles,
                    "max_latency_ms": artifact.config.max_latency_ms,
                    "coverage_threshold": artifact.config.coverage_threshold,
                    "confidence_threshold": artifact.config.confidence_threshold,
                    "enable_coverage_check": artifact.config.enable_coverage_check,
                    "enable_cross_references": artifact.config.enable_cross_references,
                },
                "iterations": [
                    {
                        "iteration_number": it.iteration_number,
                        "purpose": it.purpose.value,
                        "queries": [
                            {
                                "query_id": q.query_id,
                                "query_type": q.query_type,
                                "query_text": q.query_text,
                                "query_language": q.query_language,
                                "hypothetical_generated": q.hypothetical_generated,
                                "articles_found": q.articles_found,
                                "similarities": q.similarities,
                                "hyde_latency_ms": q.hyde_latency_ms,
                                "embedding_latency_ms": q.embedding_latency_ms,
                                "search_latency_ms": q.search_latency_ms,
                                "total_latency_ms": q.total_latency_ms,
                            }
                            for q in it.queries
                        ],
                        "articles_retrieved": it.articles_retrieved,
                        "articles_new": it.articles_new,
                        "cross_refs_found": list(it.cross_refs_found) if it.cross_refs_found else [],
                        "coverage_before": it.coverage_before,
                        "coverage_after": it.coverage_after,
                        "gaps_identified": it.gaps_identified,
                        "llm_calls": it.llm_calls,
                        "embedding_calls": it.embedding_calls,
                        "latency_ms": it.latency_ms,
                    }
                    for it in artifact.iterations
                ],
                "final_articles": artifact.final_articles,
                "final_coverage": artifact.final_coverage,
                "stop_reason": artifact.stop_reason,
                "stop_iteration": artifact.stop_iteration,
                "total_iterations": artifact.total_iterations,
                "total_articles": artifact.total_articles,
                "total_llm_calls": artifact.total_llm_calls,
                "total_embedding_calls": artifact.total_embedding_calls,
                "total_latency_ms": artifact.total_latency_ms,
                "avg_similarity": float(artifact.avg_similarity) if artifact.avg_similarity else None,
                "top_3_similarity": float(artifact.top_3_similarity) if artifact.top_3_similarity else None,
                "coverage_score": float(artifact.coverage_score) if artifact.coverage_score else None,
                "estimated_cost_usd": float(artifact.estimated_cost_usd) if artifact.estimated_cost_usd else None,
            }

            response = (
                self.client.table("retrieval_eval_artifacts")
                .insert(row)
                .execute()
            )

            logger.info(f"Saved retrieval artifact: {artifact.artifact_id}")
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Failed to save retrieval artifact: {e}")
            # Don't fail the main flow - artifacts are for eval only
            return None
