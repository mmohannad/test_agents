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
from project.components.retriever import ArticleRetriever
from project.components.synthesizer import Synthesizer
from project.supabase_client import LegalSearchSupabaseClient
from project.llm_client import LegalSearchLLMClient

logger = make_logger(__name__)
logger.info(f"Loaded environment from {env_path}")

# Initialize clients
_supabase_client: Optional[LegalSearchSupabaseClient] = None
_llm_client: Optional[LegalSearchLLMClient] = None
_decomposer: Optional[Decomposer] = None
_retriever: Optional[ArticleRetriever] = None
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


def get_retriever() -> ArticleRetriever:
    global _retriever
    if _retriever is None:
        _retriever = ArticleRetriever(get_llm_client(), get_supabase_client())
    return _retriever


def get_synthesizer() -> Synthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = Synthesizer(get_llm_client())
    return _synthesizer


# Create ACP server
acp = FastACP.create(acp_type="sync")


HELP_MESSAGE = """
**Legal Search Agent (Tier 2)**

Performs statute-grounded legal research on POA cases.

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
2. Search the legal corpus for relevant articles
3. Synthesize findings into a legal opinion
4. Return decision: valid, invalid, valid_with_remediations, or needs_review
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

    try:
        # Parse input
        try:
            input_data = json.loads(user_message)
        except json.JSONDecodeError:
            input_data = {"application_id": user_message.strip()}

        supabase = get_supabase_client()
        decomposer = get_decomposer()
        retriever = get_retriever()
        synthesizer = get_synthesizer()

        application_id = input_data.get("application_id")
        legal_brief = input_data.get("legal_brief")

        # Load Legal Brief from Supabase if not provided
        if application_id and not legal_brief:
            logger.info(f"Loading Legal Brief for application: {application_id}")
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
        logger.info("Phase 1: Decomposing case into legal sub-issues...")

        issues = await decomposer.decompose(legal_brief)
        logger.info(f"Decomposed into {len(issues)} legal issues")

        # ========================================
        # PHASE 2: RETRIEVAL (RAG)
        # ========================================
        logger.info("Phase 2: Retrieving relevant articles...")

        issue_evidence = {}
        all_articles = []

        for issue in issues:
            logger.info(f"Searching for issue: {issue['issue_id']} - {issue['category']}")
            articles = await retriever.search_for_issue(issue)
            issue_evidence[issue["issue_id"]] = articles
            all_articles.extend(articles)

            logger.info(f"Found {len(articles)} articles for {issue['issue_id']}")

        # Deduplicate articles
        seen_articles = set()
        unique_articles = []
        for article in all_articles:
            if article["article_number"] not in seen_articles:
                seen_articles.add(article["article_number"])
                unique_articles.append(article)

        logger.info(f"Total unique articles retrieved: {len(unique_articles)}")

        # ========================================
        # PHASE 3: SYNTHESIS
        # ========================================
        logger.info("Phase 3: Synthesizing legal opinion...")

        opinion = await synthesizer.synthesize(
            legal_brief=legal_brief,
            issues=issues,
            issue_evidence=issue_evidence,
            all_articles=unique_articles
        )

        # Add metadata
        opinion["application_id"] = application_id or "direct_input"
        opinion["legal_brief_id"] = brief_id
        opinion["generated_at"] = datetime.now().isoformat()
        opinion["issues_analyzed"] = issues

        # Calculate metrics
        issues_with_articles = sum(1 for eid, arts in issue_evidence.items() if arts)
        opinion["retrieval_coverage"] = issues_with_articles / len(issues) if issues else 0

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
    lines.extend([
        "---",
        "",
        "## Verification Metrics",
        "",
        f"- **Grounding Score:** {opinion.get('grounding_score', 0):.0%}",
        f"- **Retrieval Coverage:** {opinion.get('retrieval_coverage', 0):.0%}",
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
