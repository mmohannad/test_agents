"""
Retrieval Agent - Orchestrates the Agentic RAG Loop.

This is the main orchestrator that coordinates:
1. HyDE hypothetical generation
2. Semantic search with embeddings
3. Coverage analysis
4. Gap-filling iteration
5. Cross-reference expansion
"""
import asyncio
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from agentex.lib.utils.logging import make_logger

from project.models.retrieval_state import (
    RetrievalState,
    RetrievalConfig,
    RetrievalEvalArtifact,
    IterationLog,
    QueryLog,
    ArticleResult,
    IterationPurpose,
    StopReason,
)
from project.components.hyde_generator import HydeGenerator
from project.components.coverage_analyzer import CoverageAnalyzer
from project.components.crossref_expander import CrossRefExpander

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient
    from project.supabase_client import LegalSearchSupabaseClient

logger = make_logger(__name__)


class RetrievalAgent:
    """
    Agentic RAG retrieval system with HyDE and iterative refinement.

    Orchestrates the multi-phase retrieval process:
    - Phase 1: Broad retrieval with HyDE
    - Phase 2: Gap-filling for missing legal areas
    - Phase 3: Cross-reference expansion
    """

    def __init__(
        self,
        llm_client: "LegalSearchLLMClient",
        supabase_client: "LegalSearchSupabaseClient",
        config: Optional[RetrievalConfig] = None
    ):
        self.llm = llm_client
        self.supabase = supabase_client
        self.config = config or RetrievalConfig()

        # Initialize components
        self.hyde = HydeGenerator(llm_client)
        self.coverage = CoverageAnalyzer(llm_client)
        self.crossref = CrossRefExpander(supabase_client)

    async def retrieve(
        self,
        issues: list[dict],
        legal_brief: dict,
        application_id: str = "unknown"
    ) -> tuple[list[ArticleResult], RetrievalEvalArtifact]:
        """
        Main retrieval entry point with agentic loop.

        Args:
            issues: Decomposed legal issues from the decomposer
            legal_brief: The legal brief for context
            application_id: Application ID for tracking

        Returns:
            Tuple of (list of ArticleResults, evaluation artifact)
        """
        start_time = time.time()

        # Initialize state
        state = RetrievalState(application_id=application_id)

        # Determine required legal areas based on transaction type
        transaction_type = legal_brief.get("case_summary", {}).get("transaction_type")
        has_entity = bool(legal_brief.get("entity_information", {}).get("company_name_ar"))
        required_areas = self.coverage.get_required_areas(transaction_type, has_entity)

        logger.info(f"Starting agentic retrieval for {application_id}")
        logger.info(f"Transaction type: {transaction_type}, Entity: {has_entity}")
        logger.info(f"Required areas: {list(required_areas.keys())}")

        # Main agentic loop
        while True:
            state.iteration += 1
            iteration_start = time.time()

            logger.info(f"=== ITERATION {state.iteration} ===")

            # Determine iteration purpose
            if state.iteration == 1:
                purpose = IterationPurpose.BROAD_RETRIEVAL
            elif state.iteration == 2:
                purpose = IterationPurpose.GAP_FILLING
            else:
                purpose = IterationPurpose.REFERENCE_EXPANSION

            iteration_log = IterationLog(
                iteration_number=state.iteration,
                purpose=purpose
            )

            # Get coverage before this iteration
            current_articles = list(state.articles.values())
            if current_articles:
                coverage_before = self.coverage.analyze_coverage(current_articles, required_areas)
                iteration_log.coverage_before = self.coverage.get_coverage_summary(coverage_before)
            else:
                iteration_log.coverage_before = {area: "missing" for area in required_areas}

            # Execute iteration based on purpose
            if purpose == IterationPurpose.BROAD_RETRIEVAL:
                await self._execute_broad_retrieval(state, issues, iteration_log)

            elif purpose == IterationPurpose.GAP_FILLING:
                # Identify gaps
                coverage = self.coverage.analyze_coverage(
                    list(state.articles.values()),
                    required_areas
                )
                gaps = self.coverage.identify_gaps(coverage)
                iteration_log.gaps_identified = [g["area_id"] for g in gaps]

                if gaps:
                    await self._execute_gap_filling(state, gaps, iteration_log)
                else:
                    logger.info("No gaps to fill, skipping gap-filling iteration")

            elif purpose == IterationPurpose.REFERENCE_EXPANSION:
                if self.config.enable_cross_references:
                    await self._execute_reference_expansion(state, iteration_log)

            # Calculate iteration metrics
            iteration_log.latency_ms = int((time.time() - iteration_start) * 1000)
            state.total_latency_ms += iteration_log.latency_ms

            # Get coverage after this iteration
            current_articles = list(state.articles.values())
            coverage_after = self.coverage.analyze_coverage(current_articles, required_areas)
            iteration_log.coverage_after = self.coverage.get_coverage_summary(coverage_after)
            state.coverage = coverage_after

            # Log iteration
            state.iteration_logs.append(iteration_log)

            logger.info(f"Iteration {state.iteration} complete: {len(iteration_log.articles_new)} new articles")
            logger.info(f"Coverage: {iteration_log.coverage_after}")

            # Check end conditions
            should_stop, reason = self._check_end_conditions(state, coverage_after)
            if should_stop:
                state.stop_reason = reason
                logger.info(f"Stopping: {reason.value}")
                break

        # Build evaluation artifact
        artifact = self._build_artifact(state, legal_brief, issues)

        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"Retrieval complete in {total_time}ms: {len(state.articles)} articles")

        return list(state.articles.values()), artifact

    async def _execute_broad_retrieval(
        self,
        state: RetrievalState,
        issues: list[dict],
        iteration_log: IterationLog
    ):
        """Execute broad retrieval with HyDE for all issues."""
        logger.info("Executing broad retrieval with HyDE")

        for issue in issues:
            issue_id = issue.get("issue_id", "unknown")
            logger.info(f"Processing issue: {issue_id}")

            # Generate HyDE hypotheticals
            if self.config.hyde_enabled:
                hypotheticals, hyde_latency = await self.hyde.generate_for_issue(
                    issue,
                    num_hypotheticals=self.config.hyde_num_hypotheticals
                )
                iteration_log.llm_calls += 1
                state.total_llm_calls += 1

                # Search with each hypothetical
                for i, hypothetical in enumerate(hypotheticals):
                    query_log = QueryLog(
                        query_id=f"{issue_id}_hyde_{i}",
                        query_type="hyde",
                        query_text=issue.get("primary_question", ""),
                        query_language="arabic",
                        hypothetical_generated=hypothetical,
                        hyde_latency_ms=hyde_latency // len(hypotheticals) if hypotheticals else 0
                    )

                    articles = await self._search_with_embedding(
                        hypothetical,
                        state,
                        query_log,
                        iteration_log.iteration_number
                    )

                    iteration_log.queries.append(query_log)
                    iteration_log.embedding_calls += 1
                    state.total_embedding_calls += 1

            # Also do direct search with Arabic queries
            search_queries = issue.get("search_queries_ar", [])
            for query in search_queries[:2]:
                if query in state.queries_tried:
                    continue
                state.queries_tried.add(query)

                query_log = QueryLog(
                    query_id=f"{issue_id}_direct_{len(iteration_log.queries)}",
                    query_type="direct",
                    query_text=query,
                    query_language="arabic"
                )

                articles = await self._search_with_embedding(
                    query,
                    state,
                    query_log,
                    iteration_log.iteration_number
                )

                iteration_log.queries.append(query_log)
                iteration_log.embedding_calls += 1
                state.total_embedding_calls += 1

        # Update iteration log with new articles
        iteration_log.articles_retrieved = list(state.articles.keys())
        iteration_log.articles_new = list(state.articles.keys())  # All are new in first iteration

    async def _execute_gap_filling(
        self,
        state: RetrievalState,
        gaps: list[dict],
        iteration_log: IterationLog
    ):
        """Execute targeted retrieval to fill coverage gaps."""
        logger.info(f"Executing gap-filling for {len(gaps)} gaps")

        articles_before = set(state.articles.keys())

        for gap in gaps:
            area_id = gap["area_id"]
            logger.info(f"Filling gap: {area_id} ({gap['area_name_ar']})")

            # Use template queries for this area
            queries = gap.get("suggested_queries_ar", [])

            for query in queries[:2]:
                if query in state.queries_tried:
                    continue
                state.queries_tried.add(query)

                # Generate HyDE hypothetical for gap query
                if self.config.hyde_enabled:
                    hypothetical, hyde_latency = await self.hyde.generate_hypothetical(query)
                    iteration_log.llm_calls += 1
                    state.total_llm_calls += 1

                    if hypothetical:
                        query_log = QueryLog(
                            query_id=f"gap_{area_id}_{len(iteration_log.queries)}",
                            query_type="hyde",
                            query_text=query,
                            query_language="arabic",
                            hypothetical_generated=hypothetical,
                            hyde_latency_ms=hyde_latency
                        )

                        await self._search_with_embedding(
                            hypothetical,
                            state,
                            query_log,
                            iteration_log.iteration_number
                        )

                        iteration_log.queries.append(query_log)
                        iteration_log.embedding_calls += 1
                        state.total_embedding_calls += 1

        # Update iteration log
        articles_after = set(state.articles.keys())
        iteration_log.articles_retrieved = list(articles_after)
        iteration_log.articles_new = list(articles_after - articles_before)

    async def _execute_reference_expansion(
        self,
        state: RetrievalState,
        iteration_log: IterationLog
    ):
        """Expand article set by fetching cross-referenced articles."""
        logger.info("Executing cross-reference expansion")

        articles_before = set(state.articles.keys())
        already_fetched = set(state.articles.keys()) | state.cross_refs_fetched

        new_articles, fetched_refs = await self.crossref.expand_with_references(
            list(state.articles.values()),
            already_fetched,
            iteration_log.iteration_number,
            max_refs=10
        )

        # Add to state
        for article in new_articles:
            state.add_article(article)

        state.cross_refs_fetched.update(fetched_refs)

        # Update iteration log
        articles_after = set(state.articles.keys())
        iteration_log.articles_retrieved = list(articles_after)
        iteration_log.articles_new = list(articles_after - articles_before)
        iteration_log.cross_refs_found = fetched_refs

    async def _search_with_embedding(
        self,
        query_text: str,
        state: RetrievalState,
        query_log: QueryLog,
        iteration: int
    ) -> list[ArticleResult]:
        """Execute semantic search and update state."""
        search_start = time.time()

        try:
            # Generate embedding
            embed_start = time.time()
            embedding = await self.llm.get_embedding(query_text)
            query_log.embedding_latency_ms = int((time.time() - embed_start) * 1000)

            # Search in Supabase
            search_start_inner = time.time()
            articles = await asyncio.to_thread(
                self.supabase.semantic_search,
                query_embedding=embedding,
                language="arabic",
                limit=5,
                similarity_threshold=self.config.min_area_similarity - 0.1
            )
            query_log.search_latency_ms = int((time.time() - search_start_inner) * 1000)

            # Convert to ArticleResults and add to state
            results = []
            for article in articles:
                article_result = ArticleResult(
                    article_number=article.get("article_number"),
                    text_arabic=article.get("text_arabic", ""),
                    text_english=article.get("text_english", ""),
                    hierarchy_path=article.get("hierarchy_path", {}),
                    citation=article.get("citation", {}),
                    law_id=article.get("law_id"),
                    found_by_query=query_text[:100],
                    found_in_iteration=iteration,
                    similarity=article.get("similarity", 0)
                )

                is_new = state.add_article(article_result)
                if is_new:
                    results.append(article_result)

                query_log.articles_found.append(article_result.article_number)
                query_log.similarities.append(article_result.similarity)

            query_log.total_latency_ms = int((time.time() - search_start) * 1000)

            logger.info(
                f"Search returned {len(articles)} articles, "
                f"{len(results)} new (max sim: {max(query_log.similarities) if query_log.similarities else 0:.2%})"
            )

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            query_log.total_latency_ms = int((time.time() - search_start) * 1000)
            return []

    def _check_end_conditions(
        self,
        state: RetrievalState,
        coverage: dict
    ) -> tuple[bool, StopReason]:
        """Check if retrieval should stop."""

        # Hard limits
        if state.iteration >= self.config.max_iterations:
            return True, StopReason.MAX_ITERATIONS_REACHED

        if len(state.articles) >= self.config.max_articles:
            return True, StopReason.MAX_ARTICLES_REACHED

        if state.total_latency_ms >= self.config.max_latency_ms:
            return True, StopReason.MAX_LATENCY_REACHED

        # Coverage threshold
        if self.config.enable_coverage_check:
            coverage_score = self.coverage.calculate_coverage_score(coverage)
            if coverage_score >= self.config.coverage_threshold:
                return True, StopReason.COVERAGE_THRESHOLD_MET

        # Confidence threshold
        avg_sim = state.get_avg_similarity()
        top_3_sim = state.get_top_k_similarity(3)
        if (
            len(state.articles) >= self.config.min_articles and
            avg_sim >= self.config.confidence_threshold and
            top_3_sim >= 0.65
        ):
            return True, StopReason.CONFIDENCE_THRESHOLD_MET

        # Diminishing returns (after iteration 2)
        if state.iteration >= 2 and state.iteration_logs:
            last_iteration = state.iteration_logs[-1]
            if len(last_iteration.articles_new) <= 1:
                return True, StopReason.DIMINISHING_RETURNS

        return False, StopReason.COVERAGE_THRESHOLD_MET  # Won't be used

    def _build_artifact(
        self,
        state: RetrievalState,
        legal_brief: dict,
        issues: list[dict]
    ) -> RetrievalEvalArtifact:
        """Build the evaluation artifact from state."""
        artifact = RetrievalEvalArtifact(
            artifact_id=str(uuid.uuid4()),
            application_id=state.application_id,
            timestamp=state.started_at,
            legal_brief=legal_brief,
            decomposed_issues=issues,
            config=self.config,
            iterations=state.iteration_logs,
            final_articles=[
                {
                    "article_number": a.article_number,
                    "text_arabic": a.text_arabic[:500],
                    "text_english": a.text_english[:500] if a.text_english else "",
                    "similarity": a.similarity,
                    "found_in_iteration": a.found_in_iteration,
                    "is_cross_reference": a.is_cross_reference,
                    "matched_legal_areas": a.matched_legal_areas,
                }
                for a in state.get_articles_list()
            ],
            final_coverage={
                area_id: {
                    "status": status.status,
                    "articles": status.articles_found,
                    "avg_similarity": status.avg_similarity,
                    "required": status.required,
                }
                for area_id, status in state.coverage.items()
            },
            stop_reason=state.stop_reason.value if state.stop_reason else "unknown",
            stop_iteration=state.iteration,
            total_iterations=state.iteration,
            total_articles=len(state.articles),
            total_llm_calls=state.total_llm_calls,
            total_embedding_calls=state.total_embedding_calls,
            total_latency_ms=state.total_latency_ms,
            avg_similarity=state.get_avg_similarity(),
            top_3_similarity=state.get_top_k_similarity(3),
            coverage_score=self.coverage.calculate_coverage_score(state.coverage),
            estimated_cost_usd=self._estimate_cost(state)
        )

        return artifact

    def _estimate_cost(self, state: RetrievalState) -> float:
        """Estimate USD cost for the retrieval."""
        # Approximate costs (as of 2024)
        llm_cost_per_call = 0.001  # GPT-4o-mini
        embedding_cost_per_call = 0.0001  # text-embedding-3-small

        return (
            state.total_llm_calls * llm_cost_per_call +
            state.total_embedding_calls * embedding_cost_per_call
        )
