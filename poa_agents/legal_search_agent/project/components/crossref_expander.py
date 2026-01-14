"""
Cross-Reference Expander Component.

Detects references to other articles in retrieved text and
fetches those referenced articles to enable multi-hop reasoning.
"""
import re
from typing import TYPE_CHECKING

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.supabase_client import LegalSearchSupabaseClient
    from project.models.retrieval_state import ArticleResult

logger = make_logger(__name__)


# Regex patterns for detecting article references in Arabic text
CROSS_REFERENCE_PATTERNS = [
    # المادة (5) or المادة 5
    (r"المادة\s*\(?\s*(\d+)\s*\)?", "direct"),
    # المواد (5، 6، 7)
    (r"المواد\s*\(?\s*(\d+(?:\s*[،,و]\s*\d+)*)\s*\)?", "multiple"),
    # وفقاً للمادة (5)
    (r"وفقاً للمادة\s*\(?\s*(\d+)\s*\)?", "reference"),
    # بموجب المادة (5)
    (r"بموجب المادة\s*\(?\s*(\d+)\s*\)?", "reference"),
    # انظر المادة (5)
    (r"انظر المادة\s*\(?\s*(\d+)\s*\)?", "see"),
    # طبقاً للمادة (5)
    (r"طبقاً للمادة\s*\(?\s*(\d+)\s*\)?", "reference"),
    # المشار إليها في المادة (5)
    (r"المشار إليها في المادة\s*\(?\s*(\d+)\s*\)?", "reference"),
    # الفقرة ... من المادة (5)
    (r"من المادة\s*\(?\s*(\d+)\s*\)?", "reference"),
    # Article 5 (English)
    (r"Article\s+(\d+)", "english"),
]


class CrossRefExpander:
    """Expands article set by fetching cross-referenced articles."""

    def __init__(self, supabase_client: "LegalSearchSupabaseClient"):
        self.supabase = supabase_client

    def extract_references(
        self,
        text: str,
        source_article_number: int | None = None
    ) -> list[int]:
        """
        Extract article references from text.

        Args:
            text: The text to scan for references
            source_article_number: The source article (to exclude self-references)

        Returns:
            List of referenced article numbers
        """
        references = set()

        for pattern, ref_type in CROSS_REFERENCE_PATTERNS:
            matches = re.finditer(pattern, text, re.UNICODE)

            for match in matches:
                ref_text = match.group(1)

                if ref_type == "multiple":
                    # Parse multiple article numbers
                    # Handle: "5، 6، 7" or "5, 6, 7" or "5 و 6 و 7"
                    numbers = re.findall(r"\d+", ref_text)
                    for num_str in numbers:
                        try:
                            ref_num = int(num_str)
                            if self._is_valid_reference(ref_num, source_article_number):
                                references.add(ref_num)
                        except ValueError:
                            continue
                else:
                    # Single article number
                    try:
                        ref_num = int(ref_text)
                        if self._is_valid_reference(ref_num, source_article_number):
                            references.add(ref_num)
                    except ValueError:
                        continue

        return sorted(references)

    def _is_valid_reference(
        self,
        ref_num: int,
        source_article_number: int | None
    ) -> bool:
        """Check if reference is valid."""
        # Exclude self-references
        if source_article_number and ref_num == source_article_number:
            return False

        # Basic sanity check on article number range
        # Qatari Civil Code has ~1200 articles, test articles are 90001-90006
        if ref_num < 1:
            return False
        if ref_num > 100000:
            return False

        return True

    def find_all_references(
        self,
        articles: list["ArticleResult"]
    ) -> dict[int, list[int]]:
        """
        Find all cross-references in a set of articles.

        Args:
            articles: List of articles to scan

        Returns:
            Dict mapping source article number -> list of referenced articles
        """
        all_refs = {}

        for article in articles:
            text = article.text_arabic or ""
            refs = self.extract_references(text, article.article_number)

            if refs:
                all_refs[article.article_number] = refs
                logger.info(
                    f"Article {article.article_number} references: {refs}"
                )

        return all_refs

    def get_unique_references(
        self,
        articles: list["ArticleResult"],
        already_fetched: set[int]
    ) -> set[int]:
        """
        Get unique article numbers that need to be fetched.

        Args:
            articles: Current article set
            already_fetched: Article numbers already in the set

        Returns:
            Set of article numbers to fetch
        """
        to_fetch = set()

        for article in articles:
            text = article.text_arabic or ""
            refs = self.extract_references(text, article.article_number)

            for ref in refs:
                if ref not in already_fetched:
                    to_fetch.add(ref)

        return to_fetch

    async def fetch_referenced_articles(
        self,
        article_numbers: list[int],
        source_article: int | None = None
    ) -> list[dict]:
        """
        Fetch articles by their numbers.

        Args:
            article_numbers: List of article numbers to fetch
            source_article: The article that referenced these (for logging)

        Returns:
            List of article dicts
        """
        fetched = []

        for art_num in article_numbers:
            try:
                article = self.supabase.get_article_by_number(art_num)
                if article:
                    fetched.append(article)
                    logger.info(f"Fetched referenced Article {art_num}")
                else:
                    logger.warning(f"Referenced Article {art_num} not found")
            except Exception as e:
                logger.error(f"Failed to fetch Article {art_num}: {e}")

        return fetched

    def create_article_result(
        self,
        article_dict: dict,
        referenced_by: int,
        iteration: int
    ) -> "ArticleResult":
        """
        Create an ArticleResult from a fetched article dict.

        Args:
            article_dict: Raw article from database
            referenced_by: The article that referenced this one
            iteration: Current iteration number

        Returns:
            ArticleResult instance
        """
        from project.models.retrieval_state import ArticleResult

        return ArticleResult(
            article_number=article_dict.get("article_number"),
            text_arabic=article_dict.get("text_arabic", ""),
            text_english=article_dict.get("text_english", ""),
            hierarchy_path=article_dict.get("hierarchy_path", {}),
            found_by_query=f"cross_reference_from_{referenced_by}",
            found_in_iteration=iteration,
            similarity=0.8,  # Assign high similarity for cross-references
            is_cross_reference=True,
            referenced_by=referenced_by
        )

    async def expand_with_references(
        self,
        articles: list["ArticleResult"],
        already_fetched: set[int],
        iteration: int,
        max_refs: int = 10
    ) -> tuple[list["ArticleResult"], list[int]]:
        """
        Expand article set by fetching cross-referenced articles.

        Args:
            articles: Current article set
            already_fetched: Article numbers already fetched
            iteration: Current iteration number
            max_refs: Maximum references to fetch

        Returns:
            Tuple of (new ArticleResults, list of fetched article numbers)
        """
        # Find all unique references
        to_fetch = self.get_unique_references(articles, already_fetched)

        if not to_fetch:
            logger.info("No new cross-references to fetch")
            return [], []

        # Limit the number of references
        to_fetch_list = sorted(to_fetch)[:max_refs]
        logger.info(f"Fetching {len(to_fetch_list)} cross-referenced articles: {to_fetch_list}")

        # Build a map of which article referenced what
        ref_sources = {}
        for article in articles:
            refs = self.extract_references(article.text_arabic or "", article.article_number)
            for ref in refs:
                if ref in to_fetch_list and ref not in ref_sources:
                    ref_sources[ref] = article.article_number

        # Fetch the articles
        fetched_dicts = await self.fetch_referenced_articles(to_fetch_list)

        # Convert to ArticleResults
        new_articles = []
        for article_dict in fetched_dicts:
            art_num = article_dict.get("article_number")
            referenced_by = ref_sources.get(art_num, 0)

            article_result = self.create_article_result(
                article_dict,
                referenced_by=referenced_by,
                iteration=iteration
            )
            new_articles.append(article_result)

        return new_articles, to_fetch_list
