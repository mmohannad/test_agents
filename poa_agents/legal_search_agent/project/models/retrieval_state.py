"""
State models for the Agentic RAG retrieval system.

These dataclasses track state across iterations and capture
evaluation artifacts for analysis.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class IterationPurpose(str, Enum):
    """Purpose of each iteration in the agentic loop."""
    BROAD_RETRIEVAL = "broad_retrieval"
    GAP_FILLING = "gap_filling"
    REFERENCE_EXPANSION = "reference_expansion"


class StopReason(str, Enum):
    """Reasons for stopping the retrieval loop."""
    COVERAGE_THRESHOLD_MET = "coverage_threshold_met"
    CONFIDENCE_THRESHOLD_MET = "confidence_threshold_met"
    AGENT_SELF_ASSESSMENT = "agent_self_assessment"
    DIMINISHING_RETURNS = "diminishing_returns"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    MAX_ARTICLES_REACHED = "max_articles_reached"
    MAX_LATENCY_REACHED = "max_latency_reached"
    ERROR = "error"


@dataclass
class RetrievalConfig:
    """Configuration for the retrieval system."""
    # HyDE settings
    hyde_enabled: bool = True
    hyde_language: str = "arabic"
    hyde_num_hypotheticals: int = 2
    hyde_temperature: float = 0.7

    # Agentic loop settings
    max_iterations: int = 3
    max_articles: int = 30
    max_latency_ms: int = 30000
    max_llm_calls: int = 15

    # Thresholds
    coverage_threshold: float = 0.8
    confidence_threshold: float = 0.55
    min_articles: int = 5
    min_area_similarity: float = 0.5

    # Feature flags
    enable_cross_references: bool = True
    enable_coverage_check: bool = True
    save_artifacts: bool = True


@dataclass
class QueryLog:
    """Log for a single query execution."""
    query_id: str
    query_type: str  # "direct", "hyde"
    query_text: str
    query_language: str

    # HyDE specific
    hypothetical_generated: Optional[str] = None

    # Results
    articles_found: list[int] = field(default_factory=list)
    similarities: list[float] = field(default_factory=list)

    # Timing
    hyde_latency_ms: int = 0
    embedding_latency_ms: int = 0
    search_latency_ms: int = 0
    total_latency_ms: int = 0


@dataclass
class ArticleResult:
    """An article with retrieval metadata."""
    article_number: int
    text_arabic: str
    text_english: str
    hierarchy_path: dict

    # Retrieval info
    found_by_query: str
    found_in_iteration: int
    similarity: float

    # Cross-reference info
    is_cross_reference: bool = False
    referenced_by: Optional[int] = None

    # Coverage info
    matched_legal_areas: list[str] = field(default_factory=list)


@dataclass
class CoverageStatus:
    """Status of coverage for a legal area."""
    area_id: str
    area_name_en: str
    area_name_ar: str
    required: bool

    # Results
    articles_found: list[int] = field(default_factory=list)
    avg_similarity: float = 0.0
    max_similarity: float = 0.0

    # Status
    status: Literal["covered", "weak", "missing"] = "missing"

    def is_satisfied(self, min_similarity: float = 0.5) -> bool:
        """Check if this area's requirements are satisfied."""
        return (
            len(self.articles_found) >= 1 and
            self.avg_similarity >= min_similarity
        )


@dataclass
class IterationLog:
    """Log for a single iteration of the retrieval loop."""
    iteration_number: int
    purpose: IterationPurpose

    # Queries executed
    queries: list[QueryLog] = field(default_factory=list)

    # Coverage before/after
    coverage_before: dict[str, str] = field(default_factory=dict)
    coverage_after: dict[str, str] = field(default_factory=dict)
    gaps_identified: list[str] = field(default_factory=list)

    # Articles
    articles_retrieved: list[int] = field(default_factory=list)
    articles_new: list[int] = field(default_factory=list)
    cross_refs_found: list[int] = field(default_factory=list)

    # Metrics
    llm_calls: int = 0
    embedding_calls: int = 0
    latency_ms: int = 0

    # Agent reasoning (if applicable)
    agent_reasoning: Optional[str] = None


@dataclass
class RetrievalState:
    """State maintained across iterations of the agentic loop."""
    # Identification
    application_id: str
    started_at: datetime = field(default_factory=datetime.now)

    # Iteration tracking
    iteration: int = 0
    iteration_logs: list[IterationLog] = field(default_factory=list)

    # Articles (article_number -> ArticleResult)
    articles: dict[int, ArticleResult] = field(default_factory=dict)

    # Coverage tracking
    coverage: dict[str, CoverageStatus] = field(default_factory=dict)

    # Query deduplication
    queries_tried: set[str] = field(default_factory=set)

    # Cross-reference tracking
    cross_refs_fetched: set[int] = field(default_factory=set)
    cross_refs_pending: set[int] = field(default_factory=set)

    # Metrics
    total_llm_calls: int = 0
    total_embedding_calls: int = 0
    total_latency_ms: int = 0

    # Stop info
    stop_reason: Optional[StopReason] = None

    def add_article(self, article: ArticleResult) -> bool:
        """Add an article, return True if it's new."""
        if article.article_number in self.articles:
            # Update if higher similarity
            existing = self.articles[article.article_number]
            if article.similarity > existing.similarity:
                self.articles[article.article_number] = article
            return False
        self.articles[article.article_number] = article
        return True

    def get_articles_list(self) -> list[ArticleResult]:
        """Get all articles sorted by similarity."""
        return sorted(
            self.articles.values(),
            key=lambda x: x.similarity,
            reverse=True
        )

    def get_avg_similarity(self) -> float:
        """Get average similarity across all articles."""
        if not self.articles:
            return 0.0
        return sum(a.similarity for a in self.articles.values()) / len(self.articles)

    def get_top_k_similarity(self, k: int = 3) -> float:
        """Get average similarity of top-k articles."""
        articles = self.get_articles_list()
        if len(articles) < k:
            return self.get_avg_similarity()
        return sum(a.similarity for a in articles[:k]) / k


@dataclass
class RetrievalEvalArtifact:
    """Complete evaluation artifact for a retrieval session."""
    # Identification
    artifact_id: str
    application_id: str
    timestamp: datetime

    # Input
    legal_brief: dict
    decomposed_issues: list[dict]

    # Configuration used
    config: RetrievalConfig

    # Iteration details
    iterations: list[IterationLog] = field(default_factory=list)

    # Final output
    final_articles: list[dict] = field(default_factory=list)
    final_coverage: dict[str, dict] = field(default_factory=dict)

    # Stop info
    stop_reason: str = ""
    stop_iteration: int = 0

    # Aggregate metrics
    total_iterations: int = 0
    total_articles: int = 0
    total_llm_calls: int = 0
    total_embedding_calls: int = 0
    total_latency_ms: int = 0

    # Quality metrics
    avg_similarity: float = 0.0
    top_3_similarity: float = 0.0
    coverage_score: float = 0.0

    # Cost estimate
    estimated_cost_usd: float = 0.0

    # Downstream result (filled after synthesis)
    verdict: Optional[str] = None
    verdict_confidence: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "artifact_id": self.artifact_id,
            "application_id": self.application_id,
            "timestamp": self.timestamp.isoformat(),
            "legal_brief": self.legal_brief,
            "decomposed_issues": self.decomposed_issues,
            "config": {
                "hyde_enabled": self.config.hyde_enabled,
                "max_iterations": self.config.max_iterations,
                "coverage_threshold": self.config.coverage_threshold,
            },
            "iterations": [
                {
                    "iteration_number": it.iteration_number,
                    "purpose": it.purpose.value,
                    "queries": [
                        {
                            "query_type": q.query_type,
                            "query_text": q.query_text[:200],
                            "hypothetical": q.hypothetical_generated[:200] if q.hypothetical_generated else None,
                            "articles_found": q.articles_found,
                            "similarities": q.similarities,
                        }
                        for q in it.queries
                    ],
                    "coverage_before": it.coverage_before,
                    "coverage_after": it.coverage_after,
                    "gaps_identified": it.gaps_identified,
                    "articles_new": it.articles_new,
                    "latency_ms": it.latency_ms,
                }
                for it in self.iterations
            ],
            "final_articles": self.final_articles,
            "final_coverage": self.final_coverage,
            "stop_reason": self.stop_reason,
            "stop_iteration": self.stop_iteration,
            "total_iterations": self.total_iterations,
            "total_articles": self.total_articles,
            "avg_similarity": self.avg_similarity,
            "coverage_score": self.coverage_score,
            "estimated_cost_usd": self.estimated_cost_usd,
            "verdict": self.verdict,
        }
