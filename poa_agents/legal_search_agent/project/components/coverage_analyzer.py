"""
Coverage Analyzer Component.

Analyzes which legal areas are covered by retrieved articles
and identifies gaps that need additional retrieval.
"""
import os
import yaml
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient
    from project.models.retrieval_state import ArticleResult, CoverageStatus

logger = make_logger(__name__)


# Load legal areas config
CONFIG_PATH = Path(__file__).parent.parent / "config" / "legal_areas.yaml"


def load_legal_areas_config() -> dict:
    """Load legal areas configuration from YAML."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load legal areas config: {e}")
        return {"legal_areas": {}, "transaction_requirements": {}}


LEGAL_AREAS_CONFIG = load_legal_areas_config()


COVERAGE_ANALYSIS_PROMPT = """أنت محلل قانوني تقيّم مدى تغطية الأدلة القانونية.

السؤال القانوني الأصلي:
{original_question}

المواد القانونية المسترجعة:
{articles_summary}

المجالات القانونية المغطاة حالياً:
{coverage_summary}

المجالات الناقصة أو الضعيفة:
{gaps_summary}

هل لدينا أدلة كافية للإجابة على السؤال القانوني بثقة؟

أجب بصيغة JSON:
{{
    "sufficient": true/false,
    "confidence": 0.0-1.0,
    "reasoning_ar": "تحليل بالعربية",
    "missing_areas": ["area1", "area2"],
    "suggested_queries_ar": ["استعلام 1", "استعلام 2"]
}}"""


class CoverageAnalyzer:
    """Analyzes legal area coverage in retrieved articles."""

    def __init__(self, llm_client: Optional["LegalSearchLLMClient"] = None):
        self.llm = llm_client
        self.config = LEGAL_AREAS_CONFIG.get("legal_areas", {})
        self.transaction_requirements = LEGAL_AREAS_CONFIG.get("transaction_requirements", {})

    def get_required_areas(
        self,
        transaction_type: Optional[str] = None,
        has_entity: bool = False
    ) -> dict[str, dict]:
        """
        Get the required legal areas for a transaction type.

        Args:
            transaction_type: The transaction type code (e.g., "POA_SPECIAL_COMPANY")
            has_entity: Whether the case involves a company/entity

        Returns:
            Dict of area_id -> area config
        """
        # Get transaction-specific requirements
        tx_config = self.transaction_requirements.get(
            transaction_type,
            LEGAL_AREAS_CONFIG.get("default_requirements", {})
        )

        required_area_ids = tx_config.get("required_areas", [])
        conditional_area_ids = tx_config.get("conditional_areas", [])

        result = {}

        for area_id, area_config in self.config.items():
            if area_id in required_area_ids:
                result[area_id] = {**area_config, "required": True}
            elif area_id in conditional_area_ids:
                # Check conditions
                condition = area_config.get("conditional_on")
                if condition == "entity_involved" and has_entity:
                    result[area_id] = {**area_config, "required": True}
                else:
                    result[area_id] = {**area_config, "required": False}

        return result

    def analyze_coverage(
        self,
        articles: list["ArticleResult"],
        required_areas: dict[str, dict]
    ) -> dict[str, "CoverageStatus"]:
        """
        Analyze which legal areas are covered by the articles.

        Args:
            articles: List of retrieved articles
            required_areas: Required legal areas config

        Returns:
            Dict of area_id -> CoverageStatus
        """
        from project.models.retrieval_state import CoverageStatus

        coverage = {}

        for area_id, area_config in required_areas.items():
            # Find articles matching this area
            matching_articles = self._find_matching_articles(
                articles,
                area_config.get("keywords_ar", []),
                area_config.get("keywords_en", [])
            )

            # Calculate metrics
            article_numbers = [a.article_number for a in matching_articles]
            similarities = [a.similarity for a in matching_articles]
            avg_sim = sum(similarities) / len(similarities) if similarities else 0.0
            max_sim = max(similarities) if similarities else 0.0

            # Determine status
            min_sim = area_config.get("min_similarity", 0.5)
            min_articles = area_config.get("min_articles", 1)

            if len(matching_articles) >= min_articles and avg_sim >= min_sim:
                status = "covered"
            elif len(matching_articles) > 0:
                status = "weak"
            else:
                status = "missing"

            coverage[area_id] = CoverageStatus(
                area_id=area_id,
                area_name_en=area_config.get("name_en", area_id),
                area_name_ar=area_config.get("name_ar", area_id),
                required=area_config.get("required", False),
                articles_found=article_numbers,
                avg_similarity=avg_sim,
                max_similarity=max_sim,
                status=status
            )

            # Update articles with matched areas
            for article in matching_articles:
                if area_id not in article.matched_legal_areas:
                    article.matched_legal_areas.append(area_id)

        return coverage

    def _find_matching_articles(
        self,
        articles: list["ArticleResult"],
        keywords_ar: list[str],
        keywords_en: list[str]
    ) -> list["ArticleResult"]:
        """Find articles that match any of the keywords."""
        matching = []

        for article in articles:
            text_combined = (
                (article.text_arabic or "") + " " +
                (article.text_english or "")
            ).lower()

            # Check Arabic keywords
            for kw in keywords_ar:
                if kw in text_combined:
                    matching.append(article)
                    break
            else:
                # Check English keywords
                for kw in keywords_en:
                    if kw.lower() in text_combined:
                        matching.append(article)
                        break

        return matching

    def identify_gaps(
        self,
        coverage: dict[str, "CoverageStatus"]
    ) -> list[dict]:
        """
        Identify gaps in coverage that need additional retrieval.

        Returns list of gaps with suggested queries.
        """
        gaps = []

        for area_id, status in coverage.items():
            if status.required and status.status in ("missing", "weak"):
                area_config = self.config.get(area_id, {})

                gap = {
                    "area_id": area_id,
                    "area_name_ar": status.area_name_ar,
                    "area_name_en": status.area_name_en,
                    "status": status.status,
                    "suggested_queries_ar": area_config.get("template_queries_ar", []),
                    "keywords_ar": area_config.get("keywords_ar", []),
                }
                gaps.append(gap)

        return gaps

    def calculate_coverage_score(
        self,
        coverage: dict[str, "CoverageStatus"]
    ) -> float:
        """
        Calculate overall coverage score (0-1).

        Based on percentage of required areas that are covered.
        """
        required_areas = [s for s in coverage.values() if s.required]

        if not required_areas:
            return 1.0

        covered_count = sum(
            1 for s in required_areas
            if s.status == "covered"
        )

        return covered_count / len(required_areas)

    def is_coverage_sufficient(
        self,
        coverage: dict[str, "CoverageStatus"],
        threshold: float = 0.8
    ) -> bool:
        """Check if coverage meets the threshold."""
        score = self.calculate_coverage_score(coverage)
        return score >= threshold

    async def agent_assess_coverage(
        self,
        articles: list["ArticleResult"],
        coverage: dict[str, "CoverageStatus"],
        original_question: str
    ) -> dict:
        """
        Use LLM to assess if coverage is sufficient.

        This provides a more nuanced assessment than rule-based checking.
        """
        if not self.llm:
            return {"sufficient": False, "confidence": 0.0, "reasoning_ar": "LLM not available"}

        # Build summaries
        articles_summary = "\n".join([
            f"- المادة {a.article_number}: {a.text_arabic[:200]}... (التشابه: {a.similarity:.0%})"
            for a in articles[:10]
        ])

        coverage_summary = "\n".join([
            f"- {s.area_name_ar}: {s.status} ({len(s.articles_found)} مواد، تشابه: {s.avg_similarity:.0%})"
            for s in coverage.values()
        ])

        gaps = self.identify_gaps(coverage)
        gaps_summary = "\n".join([
            f"- {g['area_name_ar']}: {g['status']}"
            for g in gaps
        ]) or "لا يوجد ثغرات"

        prompt = COVERAGE_ANALYSIS_PROMPT.format(
            original_question=original_question,
            articles_summary=articles_summary,
            coverage_summary=coverage_summary,
            gaps_summary=gaps_summary
        )

        try:
            import json
            response = await self.llm.chat(
                user_message=prompt,
                system_message="أنت محلل قانوني متخصص في تقييم الأدلة.",
                temperature=0.2,
                max_tokens=500
            )

            # Parse JSON response
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]

            return json.loads(clean_response.strip())

        except Exception as e:
            logger.error(f"Agent assessment failed: {e}")
            return {
                "sufficient": False,
                "confidence": 0.0,
                "reasoning_ar": f"فشل التقييم: {str(e)}",
                "missing_areas": [],
                "suggested_queries_ar": []
            }

    def get_coverage_summary(
        self,
        coverage: dict[str, "CoverageStatus"]
    ) -> dict[str, str]:
        """Get a simple status summary for logging."""
        return {
            area_id: status.status
            for area_id, status in coverage.items()
        }
