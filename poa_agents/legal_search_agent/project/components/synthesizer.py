"""
Synthesizer Component - Generates legal opinion from evidence.
"""
import json
from typing import TYPE_CHECKING

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient

logger = make_logger(__name__)


SYNTHESIS_SYSTEM_PROMPT = """You are a senior legal analyst producing detailed legal opinions for notarization applications.

Your task is to:
1. Analyze each legal issue identified
2. Apply the relevant legal articles to the facts
3. Produce a comprehensive, well-reasoned legal opinion
4. Cite specific articles with exact quotes to support each conclusion

OPINION STRUCTURE:
- Start with a clear CASE SUMMARY
- Address each LEGAL ISSUE with detailed analysis
- Provide CLEAR CITATIONS with article numbers and relevant text
- Give a final DETERMINATION with reasoning

CITATION REQUIREMENTS:
- Every legal conclusion MUST cite specific article(s)
- Quote the relevant portion of the article
- Explain HOW the article applies to the specific facts

Your opinion will be reviewed by legal professionals. Be thorough, precise, and well-reasoned."""


SYNTHESIS_PROMPT_TEMPLATE = """Produce a comprehensive legal opinion based on the following case facts and legal research.

## LEGAL BRIEF (Case Facts):
{legal_brief}

## LEGAL ISSUES TO ANALYZE:
{issues}

## RELEVANT LEGAL ARTICLES:
{articles}

## EVIDENCE RETRIEVED PER ISSUE:
{issue_evidence}

---

Produce a detailed legal opinion with the following structure:

{{
    "case_summary": {{
        "application_type": "...",
        "parties_involved": "Brief description of parties",
        "core_question": "The main legal question to be determined",
        "key_facts": ["List the most important facts"]
    }},
    "overall_finding": "VALID|INVALID|VALID_WITH_CONDITIONS|REQUIRES_REVIEW|INCONCLUSIVE",
    "confidence_score": 0.0-1.0,
    "confidence_level": "HIGH|MEDIUM|LOW",
    "decision_bucket": "valid|valid_with_remediations|invalid|needs_review",
    "opinion_summary_en": "2-3 paragraph summary of the legal opinion in English",
    "opinion_summary_ar": "ملخص الرأي القانوني بالعربية - 2-3 فقرات",
    "detailed_analysis": {{
        "introduction": "Overview of the legal analysis",
        "issue_by_issue_analysis": [
            {{
                "issue_id": "ISSUE_1",
                "issue_title": "Clear title for the issue",
                "category": "capacity|authority|scope|formalities|validity|compliance",
                "facts_considered": ["Specific facts relevant to this issue"],
                "legal_analysis": "Detailed paragraph explaining the legal reasoning",
                "applicable_articles": [
                    {{
                        "article_number": 1,
                        "article_text": "EXACT quote from the article",
                        "application_to_facts": "How this article applies to the specific facts"
                    }}
                ],
                "finding": "SUPPORTED|NOT_SUPPORTED|PARTIALLY_SUPPORTED|UNCLEAR",
                "confidence": 0.0-1.0,
                "reasoning_summary": "One sentence summary of the conclusion for this issue"
            }}
        ],
        "synthesis": "How the individual issue findings combine to form the overall conclusion",
        "conclusion": "Final determination with clear reasoning"
    }},
    "citations": [
        {{
            "citation_id": "C1",
            "article_number": 2,
            "law_name": "Name of the law",
            "chapter": "Chapter/section if available",
            "quoted_text": "EXACT text being cited",
            "relevance": "Why this citation is relevant to the case"
        }}
    ],
    "concerns": ["Specific concerns about this application"],
    "recommendations": ["Specific recommendations"],
    "conditions": ["If valid_with_remediations, list specific conditions that must be met"],
    "grounding_score": 0.0-1.0
}}

IMPORTANT INSTRUCTIONS:
1. CITE EXACTLY - Quote the actual text from articles, do not paraphrase
2. BE SPECIFIC - Reference specific facts from the case
3. SHOW REASONING - Explain HOW each article applies to the facts
4. BE THOROUGH - Address every issue identified
5. BE OBJECTIVE - Present the legal analysis without bias

Return ONLY the JSON object."""


class Synthesizer:
    """Synthesizes legal opinion from Legal Brief and retrieved evidence."""

    def __init__(self, llm_client: "LegalSearchLLMClient"):
        self.llm = llm_client

    async def synthesize(
        self,
        legal_brief: dict,
        issues: list[dict],
        issue_evidence: dict[str, list[dict]],
        all_articles: list[dict]
    ) -> dict:
        """
        Synthesize a legal opinion from the evidence.

        Args:
            legal_brief: The Legal Brief
            issues: List of legal issues analyzed
            issue_evidence: Map of issue_id -> relevant articles
            all_articles: All unique articles retrieved

        Returns:
            Legal opinion dict
        """
        # Format articles for prompt
        articles_text = self._format_articles(all_articles)
        evidence_text = self._format_issue_evidence(issue_evidence)

        prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
            legal_brief=json.dumps(legal_brief, ensure_ascii=False, indent=2),
            issues=json.dumps(issues, ensure_ascii=False, indent=2),
            articles=articles_text,
            issue_evidence=evidence_text
        )

        logger.info("Calling LLM to synthesize legal opinion...")

        response = await self.llm.chat(
            user_message=prompt,
            system_message=SYNTHESIS_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=4000
        )

        # Parse response
        try:
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]

            opinion = json.loads(clean_response.strip())

            # Validate and set defaults
            opinion.setdefault("overall_finding", "INCONCLUSIVE")
            opinion.setdefault("confidence_score", 0.5)
            opinion.setdefault("confidence_level", "MEDIUM")
            opinion.setdefault("decision_bucket", "needs_review")
            opinion.setdefault("findings", [])
            opinion.setdefault("concerns", [])
            opinion.setdefault("recommendations", [])
            opinion.setdefault("all_citations", all_articles)
            opinion.setdefault("grounding_score", self._calculate_grounding(opinion))

            return opinion

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse synthesis response: {e}")
            # Return a basic opinion
            return {
                "overall_finding": "INCONCLUSIVE",
                "confidence_score": 0.3,
                "confidence_level": "LOW",
                "decision_bucket": "needs_review",
                "opinion_summary_en": "Unable to synthesize opinion. Raw analysis: " + response[:500],
                "detailed_analysis": response,
                "findings": [],
                "concerns": ["Synthesis failed - manual review required"],
                "recommendations": ["Please review the case manually"],
                "all_citations": all_articles,
                "grounding_score": 0.0
            }

    def _format_articles(self, articles: list[dict]) -> str:
        """Format articles for the prompt."""
        if not articles:
            return "No relevant articles found."

        lines = []
        for art in articles:
            lines.append(f"### Article {art.get('article_number', '?')}")
            if art.get("law_name"):
                lines.append(f"Law: {art.get('law_name')}")

            text_en = art.get("text_english") or art.get("text_en", "")
            text_ar = art.get("text_arabic") or art.get("text_ar", "")

            if text_en:
                lines.append(f"English: {text_en}")
            if text_ar:
                lines.append(f"Arabic: {text_ar}")

            lines.append(f"Similarity: {art.get('similarity', 0):.0%}")
            lines.append("")

        return "\n".join(lines)

    def _format_issue_evidence(self, issue_evidence: dict[str, list[dict]]) -> str:
        """Format issue evidence for the prompt."""
        lines = []
        for issue_id, articles in issue_evidence.items():
            lines.append(f"### {issue_id}")
            if articles:
                for art in articles:
                    lines.append(f"- Article {art.get('article_number')}: {art.get('similarity', 0):.0%}")
            else:
                lines.append("- No relevant articles found")
            lines.append("")

        return "\n".join(lines)

    def _calculate_grounding(self, opinion: dict) -> float:
        """Calculate grounding score based on citations."""
        findings = opinion.get("findings", [])
        if not findings:
            return 0.0

        grounded_findings = sum(
            1 for f in findings
            if f.get("supporting_articles")
        )

        return grounded_findings / len(findings) if findings else 0.0
