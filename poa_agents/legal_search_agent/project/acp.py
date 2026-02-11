"""
ACP server for the Legal Search Agent (Tier 2).

Performs statute-grounded legal research using:
1. Decomposition - Break case into legal sub-issues
2. Retrieval - RAG search for relevant articles
3. Synthesis - Generate legal opinion with citations
4. Verification - Check grounding and consistency
"""
import os
import sys
import json
from pathlib import Path
from typing import AsyncGenerator, Optional
from datetime import datetime

import dotenv

# Load .env file FIRST before any other imports that need env vars
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    dotenv.load_dotenv(env_path)

from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.text_content import TextContent
from agentex.lib.utils.logging import make_logger

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from project.components.decomposer import Decomposer
from project.components.retrieval_agent import RetrievalAgent
from project.components.synthesizer import Synthesizer
from project.supabase_client import LegalSearchSupabaseClient
from project.llm_client import LegalSearchLLMClient
from project.models.retrieval_state import RetrievalConfig, ArticleResult

# Import tracing
try:
    from shared.tracing import Trace, current_trace
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    Trace = None

logger = make_logger(__name__)
logger.info(f"Loaded environment from {env_path}")

# Initialize clients
_supabase_client: Optional[LegalSearchSupabaseClient] = None
_llm_client: Optional[LegalSearchLLMClient] = None
_decomposer: Optional[Decomposer] = None
_retrieval_agent: Optional[RetrievalAgent] = None
_synthesizer: Optional[Synthesizer] = None


def get_supabase_client() -> LegalSearchSupabaseClient:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = LegalSearchSupabaseClient()
    return _supabase_client


def get_llm_client() -> LegalSearchLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LegalSearchLLMClient()
    return _llm_client


def get_decomposer() -> Decomposer:
    global _decomposer
    if _decomposer is None:
        _decomposer = Decomposer(get_llm_client())
    return _decomposer


def get_retrieval_agent() -> RetrievalAgent:
    """Get the agentic retrieval system with HyDE and iterative refinement."""
    global _retrieval_agent
    if _retrieval_agent is None:
        config = RetrievalConfig(
            hyde_enabled=True,
            hyde_num_hypotheticals=2,
            max_iterations=3,
            max_articles=30,
            max_latency_ms=600000,  # 60 seconds to allow HyDE generation time
            coverage_threshold=0.8,
            confidence_threshold=0.55,
            enable_coverage_check=True,
            enable_cross_references=True,
        )
        _retrieval_agent = RetrievalAgent(
            get_llm_client(),
            get_supabase_client(),
            config
        )
    return _retrieval_agent


def get_synthesizer() -> Synthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = Synthesizer(get_llm_client())
    return _synthesizer


def article_result_to_dict(article: ArticleResult) -> dict:
    """Convert ArticleResult to dict format expected by synthesizer."""
    return {
        "article_number": article.article_number,
        "law_id": article.law_id,
        "text_arabic": article.text_arabic,
        "text_english": article.text_english,
        "text_ar": article.text_arabic,  # Alias for compatibility
        "text_en": article.text_english,  # Alias for compatibility
        "hierarchy_path": article.hierarchy_path,
        "citation": article.citation,  # Rich citation info from poa_articles
        "similarity": article.similarity,
        "found_by_query": article.found_by_query,
        "found_in_iteration": article.found_in_iteration,
        "is_cross_reference": article.is_cross_reference,
        "matched_legal_areas": article.matched_legal_areas,
    }


# Create ACP server
acp = FastACP.create(acp_type="sync")


HELP_MESSAGE = """
**Legal Search Agent (Tier 2) - Agentic RAG**

Performs statute-grounded legal research on POA cases using:
- **HyDE** (Hypothetical Document Embeddings) for Arabic legal search
- **Agentic RAG Loop** with iterative refinement
- **Coverage Analysis** for comprehensive legal area coverage
- **Cross-Reference Expansion** for multi-hop reasoning

**Input formats:**

1. By application ID:
```json
{"application_id": "uuid-here"}
```

2. Direct Legal Brief:
```json
{"legal_brief": {...}}
```

The agent will:
1. Decompose the case into legal sub-issues
2. **Agentic Retrieval** (up to 3 iterations):
   - Iteration 1: Broad retrieval with HyDE hypotheticals
   - Iteration 2: Gap-filling for missing legal areas
   - Iteration 3: Cross-reference expansion
3. Synthesize findings into a legal opinion
4. Return decision: valid, invalid, valid_with_remediations, or needs_review

Retrieval artifacts are saved for evaluation and debugging.
"""


@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams
) -> TaskMessageContent | list[TaskMessageContent] | AsyncGenerator[TaskMessageUpdate, None]:
    """
    Handle incoming requests for legal research.

    Input:
    - {"application_id": "uuid"} - Load Legal Brief from Supabase
    - {"legal_brief": {...}} - Direct Legal Brief input
    """
    user_message = params.content.content if params.content else ""

    if not user_message:
        return TextContent(author="agent", content=HELP_MESSAGE)

    logger.info(f"Received message: {user_message[:200]}...")

    # Parse input early to get application_id for tracing
    try:
        input_data = json.loads(user_message)
    except json.JSONDecodeError:
        input_data = {"application_id": user_message.strip()}

    application_id = input_data.get("application_id")
    locale = input_data.get("locale", "ar")

    # Create trace context if tracing is available
    trace_context = None
    if TRACING_AVAILABLE and Trace:
        trace_context = Trace(
            agent_name="legal_search",
            application_id=application_id if application_id and application_id != "direct_input" else None,
            metadata={
                "locale": locale,
                "has_legal_brief": "legal_brief" in input_data,
            }
        )
        trace_context.__enter__()
        trace_context.set_input({"message_length": len(user_message), "application_id": application_id})

    try:
        result = await _handle_legal_search_internal(input_data, application_id, locale, user_message)

        # Record output in trace
        if trace_context:
            trace_context.set_output({"status": "success"})
            trace_context.__exit__(None, None, None)

        return result

    except Exception as e:
        # Record error in trace
        if trace_context:
            trace_context.__exit__(type(e), e, e.__traceback__)
        raise


async def _handle_legal_search_internal(
    input_data: dict,
    application_id: Optional[str],
    locale: str,
    user_message: str
):
    """Internal handler logic, separated for tracing."""
    try:
        supabase = get_supabase_client()
        decomposer = get_decomposer()
        retrieval_agent = get_retrieval_agent()
        synthesizer = get_synthesizer()
        trace = current_trace() if TRACING_AVAILABLE else None

        legal_brief = input_data.get("legal_brief")

        # Load Legal Brief from Supabase if not provided
        if application_id and not legal_brief:
            logger.info(f"Loading Legal Brief for application: {application_id}")
            if trace:
                with trace.span("load_legal_brief", type="db_query") as span:
                    span.set_attribute("application_id", application_id)
                    brief_row = supabase.get_legal_brief(application_id)
                    span.set_attribute("found", brief_row is not None)
            else:
                brief_row = supabase.get_legal_brief(application_id)

            if not brief_row:
                return TextContent(
                    author="agent",
                    content=f"Legal Brief not found for application: {application_id}\n\nPlease run the Condenser Agent first."
                )
            legal_brief = brief_row.get("brief_content", {})
            brief_id = brief_row.get("id")
        else:
            brief_id = None

        if not legal_brief:
            return TextContent(
                author="agent",
                content="No Legal Brief available. Please provide application_id or legal_brief.\n\n" + HELP_MESSAGE
            )

        # ========================================
        # PHASE 1: DECOMPOSITION
        # ========================================
        logger.info(f"Phase 1: Decomposing case into legal sub-issues (locale={locale})...")

        if trace:
            with trace.span("decomposition", type="tool_call") as span:
                span.set_attribute("locale", locale)
                issues = await decomposer.decompose(legal_brief, locale=locale)
                span.set_attributes({
                    "issues_count": len(issues),
                    "issue_ids": [i.get("issue_id") for i in issues],
                })
        else:
            issues = await decomposer.decompose(legal_brief, locale=locale)

        logger.info(f"Decomposed into {len(issues)} legal issues")

        # ========================================
        # PHASE 2: AGENTIC RETRIEVAL (HyDE + RAG Loop)
        # ========================================
        logger.info("Phase 2: Agentic retrieval with HyDE and iterative refinement...")

        if trace:
            with trace.span("agentic_retrieval", type="retrieval") as span:
                span.set_attributes({
                    "issues_count": len(issues),
                    "hyde_enabled": True,
                })
                # Run the agentic retrieval loop
                article_results, retrieval_artifact = await retrieval_agent.retrieve(
                    issues=issues,
                    legal_brief=legal_brief,
                    application_id=application_id or "direct_input"
                )
                span.set_attributes({
                    "iterations": retrieval_artifact.total_iterations,
                    "articles_found": retrieval_artifact.total_articles,
                    "stop_reason": retrieval_artifact.stop_reason,
                    "coverage_score": retrieval_artifact.coverage_score,
                    "avg_similarity": retrieval_artifact.avg_similarity,
                    "llm_calls": retrieval_artifact.total_llm_calls,
                    "embedding_calls": retrieval_artifact.total_embedding_calls,
                    "latency_ms": retrieval_artifact.total_latency_ms,
                })
        else:
            article_results, retrieval_artifact = await retrieval_agent.retrieve(
                issues=issues,
                legal_brief=legal_brief,
                application_id=application_id or "direct_input"
            )

        logger.info(f"Agentic retrieval complete:")
        logger.info(f"  - Iterations: {retrieval_artifact.total_iterations}")
        logger.info(f"  - Articles: {retrieval_artifact.total_articles}")
        logger.info(f"  - Stop reason: {retrieval_artifact.stop_reason}")
        logger.info(f"  - Coverage score: {retrieval_artifact.coverage_score:.0%}")
        logger.info(f"  - Avg similarity: {retrieval_artifact.avg_similarity:.0%}")

        # Save retrieval artifact for evaluation (non-blocking)
        try:
            supabase.save_retrieval_artifact(retrieval_artifact)
        except Exception as e:
            logger.warning(f"Could not save retrieval artifact: {e}")

        # Convert ArticleResults to dicts for synthesizer
        unique_articles = [article_result_to_dict(art) for art in article_results]

        # Build issue_evidence mapping from article's matched_legal_areas
        issue_evidence = {}
        for issue in issues:
            issue_id = issue.get("issue_id", "unknown")
            # Find articles relevant to this issue based on matched areas
            issue_articles = [
                article_result_to_dict(art)
                for art in article_results
                if any(area in art.matched_legal_areas for area in [issue.get("category", "")])
            ]
            # If no matches by area, use all articles (fallback)
            if not issue_articles:
                issue_articles = unique_articles[:5]
            issue_evidence[issue_id] = issue_articles

        logger.info(f"Total unique articles retrieved: {len(unique_articles)}")

        # ========================================
        # PHASE 3: SYNTHESIS
        # ========================================
        logger.info(f"Phase 3: Synthesizing legal opinion (locale={locale})...")

        if trace:
            with trace.span("synthesis", type="tool_call") as span:
                span.set_attributes({
                    "locale": locale,
                    "issues_count": len(issues),
                    "articles_count": len(unique_articles),
                })
                opinion = await synthesizer.synthesize(
                    legal_brief=legal_brief,
                    issues=issues,
                    issue_evidence=issue_evidence,
                    all_articles=unique_articles,
                    locale=locale
                )
                span.set_attributes({
                    "finding": opinion.get("overall_finding"),
                    "decision": opinion.get("decision_bucket"),
                    "confidence": opinion.get("confidence_score"),
                })
        else:
            opinion = await synthesizer.synthesize(
                legal_brief=legal_brief,
                issues=issues,
                issue_evidence=issue_evidence,
                all_articles=unique_articles,
                locale=locale
            )

        # Add metadata
        opinion["application_id"] = application_id or "direct_input"
        opinion["legal_brief_id"] = brief_id
        opinion["generated_at"] = datetime.now().isoformat()
        opinion["issues_analyzed"] = issues

        # Add retrieval metrics from agentic loop
        opinion["retrieval_metrics"] = {
            "total_iterations": retrieval_artifact.total_iterations,
            "total_articles": retrieval_artifact.total_articles,
            "stop_reason": retrieval_artifact.stop_reason,
            "coverage_score": retrieval_artifact.coverage_score,
            "avg_similarity": retrieval_artifact.avg_similarity,
            "top_3_similarity": retrieval_artifact.top_3_similarity,
            "total_llm_calls": retrieval_artifact.total_llm_calls,
            "total_embedding_calls": retrieval_artifact.total_embedding_calls,
            "total_latency_ms": retrieval_artifact.total_latency_ms,
            "estimated_cost_usd": retrieval_artifact.estimated_cost_usd,
        }

        # Calculate metrics
        issues_with_articles = sum(1 for eid, arts in issue_evidence.items() if arts)
        opinion["retrieval_coverage"] = retrieval_artifact.coverage_score if retrieval_artifact.coverage_score else (issues_with_articles / len(issues) if issues else 0)

        # ========================================
        # PHASE 4: SAVE RESULTS
        # ========================================
        if application_id:
            try:
                supabase.save_legal_opinion(application_id, opinion, brief_id)
                logger.info(f"Saved legal opinion for application: {application_id}")
            except Exception as e:
                logger.warning(f"Could not save legal opinion: {e}")

        # Format output
        output = format_legal_opinion(opinion)

        return TextContent(author="agent", content=output)

    except Exception as e:
        logger.error(f"Error in legal research: {e}", exc_info=True)
        return TextContent(
            author="agent",
            content=f"Error performing legal research: {str(e)}"
        )


def format_legal_opinion(opinion: dict) -> str:
    """Format the legal opinion for display."""

    # Determine overall status emoji
    finding = opinion.get("overall_finding", "UNKNOWN")
    decision = opinion.get("decision_bucket", "needs_review")

    if finding == "INVALID" or decision == "invalid":
        status_emoji = "❌"
        status_color = "red"
    elif finding == "VALID" and decision == "valid":
        status_emoji = "✅"
        status_color = "green"
    elif decision == "valid_with_remediations":
        status_emoji = "⚠️"
        status_color = "yellow"
    else:
        status_emoji = "🔍"
        status_color = "blue"

    lines = [
        f"# {status_emoji} Legal Research Opinion",
        "",
        f"**Application ID:** {opinion.get('application_id', 'N/A')}",
        f"**Generated:** {opinion.get('generated_at', 'N/A')}",
        "",
        "---",
        "",
        "## Decision",
        "",
        f"### {status_emoji} Finding: **{finding}**",
        f"### Decision Bucket: **{decision.upper().replace('_', ' ')}**",
        f"### Confidence: **{opinion.get('confidence_score', 0):.0%}** ({opinion.get('confidence_level', 'N/A')})",
        "",
    ]

    # Opinion Summary
    if opinion.get("opinion_summary_en"):
        lines.extend([
            "---",
            "",
            "## Opinion Summary",
            "",
            opinion.get("opinion_summary_en"),
            ""
        ])

    if opinion.get("opinion_summary_ar"):
        lines.extend([
            "### Arabic Summary",
            "",
            opinion.get("opinion_summary_ar"),
            ""
        ])

    # Issues Analyzed
    issues = opinion.get("issues_analyzed", [])
    findings = opinion.get("findings", [])

    if issues:
        lines.extend([
            "---",
            "",
            "## Legal Issues Analyzed",
            ""
        ])

        for issue in issues:
            issue_id = issue.get("issue_id", "?")
            category = issue.get("category", "unknown")
            question = issue.get("primary_question", "")

            # Find the finding for this issue
            issue_finding = next(
                (f for f in findings if f.get("issue_id") == issue_id),
                None
            )

            if issue_finding:
                finding_status = issue_finding.get("finding", "UNCLEAR")
                if finding_status == "NOT_SUPPORTED":
                    emoji = "❌"
                elif finding_status == "SUPPORTED":
                    emoji = "✅"
                elif finding_status == "PARTIALLY_SUPPORTED":
                    emoji = "⚠️"
                else:
                    emoji = "❓"

                lines.append(f"### {emoji} {issue_id}: {category.replace('_', ' ').title()}")
                lines.append(f"**Question:** {question}")
                lines.append(f"**Finding:** {finding_status}")
                lines.append(f"**Confidence:** {issue_finding.get('confidence', 0):.0%}")
                lines.append("")

                if issue_finding.get("reasoning"):
                    lines.append(f"**Analysis:** {issue_finding.get('reasoning')}")
                    lines.append("")

                # Supporting articles
                supporting = issue_finding.get("supporting_articles", [])
                if supporting:
                    lines.append("**Supporting Articles:**")
                    for art in supporting[:3]:
                        lines.append(f"- Article {art.get('article_number')}: {art.get('text_en', '')[:200]}...")
                    lines.append("")

                # Concerns
                concerns = issue_finding.get("concerns", [])
                if concerns:
                    lines.append("**Concerns:**")
                    for c in concerns:
                        lines.append(f"- ⚠️ {c}")
                    lines.append("")

            lines.append("")

    # Overall Concerns and Recommendations
    concerns = opinion.get("concerns", [])
    if concerns:
        lines.extend([
            "---",
            "",
            "## ⚠️ Key Concerns",
            ""
        ])
        for c in concerns:
            lines.append(f"- {c}")
        lines.append("")

    recommendations = opinion.get("recommendations", [])
    if recommendations:
        lines.extend([
            "## Recommendations",
            ""
        ])
        for r in recommendations:
            lines.append(f"- {r}")
        lines.append("")

    conditions = opinion.get("conditions", [])
    if conditions:
        lines.extend([
            "## Conditions (if valid with remediations)",
            ""
        ])
        for c in conditions:
            lines.append(f"- {c}")
        lines.append("")

    # All Citations
    citations = opinion.get("all_citations", [])
    if citations:
        lines.extend([
            "---",
            "",
            "## Legal Citations",
            ""
        ])
        for art in citations[:10]:  # Limit to top 10
            lines.append(f"### Article {art.get('article_number')}")
            if art.get("law_name"):
                lines.append(f"*{art.get('law_name')}*")
            if art.get("text_en"):
                lines.append(f">{art.get('text_en')[:500]}...")
            lines.append(f"*Similarity: {art.get('similarity', 0):.0%}*")
            lines.append("")

    # Verification Metrics
    retrieval_metrics = opinion.get("retrieval_metrics", {})
    lines.extend([
        "---",
        "",
        "## Verification Metrics",
        "",
        f"- **Grounding Score:** {opinion.get('grounding_score', 0):.0%}",
        f"- **Retrieval Coverage:** {opinion.get('retrieval_coverage', 0):.0%}",
        "",
        "### Agentic Retrieval Details",
        "",
        f"- **Iterations:** {retrieval_metrics.get('total_iterations', 'N/A')}",
        f"- **Stop Reason:** {retrieval_metrics.get('stop_reason', 'N/A')}",
        f"- **Articles Retrieved:** {retrieval_metrics.get('total_articles', 'N/A')}",
        f"- **Coverage Score:** {retrieval_metrics.get('coverage_score', 0):.0%}" if retrieval_metrics.get('coverage_score') else "- **Coverage Score:** N/A",
        f"- **Avg Similarity:** {retrieval_metrics.get('avg_similarity', 0):.0%}" if retrieval_metrics.get('avg_similarity') else "- **Avg Similarity:** N/A",
        f"- **Top-3 Similarity:** {retrieval_metrics.get('top_3_similarity', 0):.0%}" if retrieval_metrics.get('top_3_similarity') else "- **Top-3 Similarity:** N/A",
        f"- **LLM Calls (HyDE):** {retrieval_metrics.get('total_llm_calls', 'N/A')}",
        f"- **Embedding Calls:** {retrieval_metrics.get('total_embedding_calls', 'N/A')}",
        f"- **Latency:** {retrieval_metrics.get('total_latency_ms', 'N/A')}ms",
        f"- **Est. Cost:** ${retrieval_metrics.get('estimated_cost_usd', 0):.4f}" if retrieval_metrics.get('estimated_cost_usd') else "- **Est. Cost:** N/A",
        ""
    ])

    # Raw JSON
    lines.extend([
        "---",
        "",
        "<details>",
        "<summary>Raw JSON Output</summary>",
        "",
        "```json",
        json.dumps(opinion, ensure_ascii=False, indent=2, default=str),
        "```",
        "</details>"
    ])

    return "\n".join(lines)
