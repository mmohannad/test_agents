"""
HyDE (Hypothetical Document Embeddings) Generator.

Generates hypothetical Arabic legal articles that would answer
a given legal question, bridging the query-document semantic gap.
"""
import time
from typing import TYPE_CHECKING

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient

logger = make_logger(__name__)


HYDE_SYSTEM_PROMPT = """أنت خبير في صياغة المواد القانونية القطرية.
مهمتك: تحويل السؤال القانوني إلى مادة قانونية افتراضية.

قواعد الصياغة:
1. ابدأ بـ "المادة (هـ):" للدلالة على أنها مادة افتراضية
2. استخدم الأسلوب التقريري القانوني (لا يجوز، يجب، يحق، يلتزم)
3. اجعل المادة موجزة (فقرة إلى فقرتين كحد أقصى)
4. استخدم المصطلحات القانونية الصحيحة بالعربية الفصحى
5. اكتب المادة كما لو كانت موجودة في القانون المدني القطري
6. لا تضف أرقام مواد حقيقية أو إشارات لمواد أخرى

الهدف: إنشاء مادة قانونية افتراضية تكون مشابهة لسانياً للمواد الحقيقية في المدونة القانونية."""


HYDE_USER_TEMPLATE = """السؤال القانوني: {question}

اكتب مادة قانونية افتراضية واحدة تجيب على هذا السؤال بشكل مباشر:"""


HYDE_MULTIPLE_TEMPLATE = """السؤال القانوني: {question}

اكتب {num_hypotheticals} مواد قانونية افتراضية مختلفة تجيب على هذا السؤال من زوايا مختلفة.

افصل بين كل مادة بسطر فارغ. كل مادة تبدأ بـ "المادة (هـ):"."""


class HydeGenerator:
    """Generates hypothetical legal articles for improved retrieval."""

    def __init__(self, llm_client: "LegalSearchLLMClient"):
        self.llm = llm_client

    async def generate_hypothetical(
        self,
        question: str,
        temperature: float = 0.7
    ) -> tuple[str, int]:
        """
        Generate a single hypothetical Arabic legal article.

        Args:
            question: The legal question to answer
            temperature: LLM temperature (higher = more creative)

        Returns:
            Tuple of (hypothetical article text, latency in ms)
        """
        start_time = time.time()

        prompt = HYDE_USER_TEMPLATE.format(question=question)

        try:
            response = await self.llm.chat(
                user_message=prompt,
                system_message=HYDE_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=500
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Clean up response
            hypothetical = response.strip()

            # Ensure it starts with the expected prefix
            if not hypothetical.startswith("المادة"):
                hypothetical = f"المادة (هـ): {hypothetical}"

            logger.info(f"Generated hypothetical ({latency_ms}ms): {hypothetical[:100]}...")

            return hypothetical, latency_ms

        except Exception as e:
            logger.error(f"Failed to generate hypothetical: {e}")
            latency_ms = int((time.time() - start_time) * 1000)
            return "", latency_ms

    async def generate_multiple_hypotheticals(
        self,
        question: str,
        num_hypotheticals: int = 2,
        temperature: float = 0.7
    ) -> tuple[list[str], int]:
        """
        Generate multiple hypothetical articles for a question.

        This provides diverse coverage of how the question might be
        answered in the legal corpus.

        Args:
            question: The legal question to answer
            num_hypotheticals: Number of hypotheticals to generate
            temperature: LLM temperature

        Returns:
            Tuple of (list of hypothetical texts, total latency in ms)
        """
        start_time = time.time()

        prompt = HYDE_MULTIPLE_TEMPLATE.format(
            question=question,
            num_hypotheticals=num_hypotheticals
        )

        try:
            response = await self.llm.chat(
                user_message=prompt,
                system_message=HYDE_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=800
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Parse multiple hypotheticals
            hypotheticals = self._parse_multiple_hypotheticals(response, num_hypotheticals)

            logger.info(f"Generated {len(hypotheticals)} hypotheticals ({latency_ms}ms)")

            return hypotheticals, latency_ms

        except Exception as e:
            logger.error(f"Failed to generate multiple hypotheticals: {e}")
            latency_ms = int((time.time() - start_time) * 1000)
            return [], latency_ms

    def _parse_multiple_hypotheticals(
        self,
        response: str,
        expected_count: int
    ) -> list[str]:
        """Parse multiple hypotheticals from LLM response."""
        hypotheticals = []

        # Try splitting by "المادة (هـ):" prefix
        parts = response.split("المادة (هـ):")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Re-add the prefix
            hypothetical = f"المادة (هـ): {part}"
            hypotheticals.append(hypothetical)

            if len(hypotheticals) >= expected_count:
                break

        # If we didn't get enough, try splitting by double newlines
        if len(hypotheticals) < expected_count:
            alt_parts = response.split("\n\n")
            for part in alt_parts:
                part = part.strip()
                if part and part not in hypotheticals:
                    if not part.startswith("المادة"):
                        part = f"المادة (هـ): {part}"
                    hypotheticals.append(part)

                    if len(hypotheticals) >= expected_count:
                        break

        # If still not enough, at least return what we have
        if len(hypotheticals) == 0 and response.strip():
            hypotheticals = [f"المادة (هـ): {response.strip()}"]

        return hypotheticals[:expected_count]

    async def generate_for_issue(
        self,
        issue: dict,
        num_hypotheticals: int = 2
    ) -> tuple[list[str], int]:
        """
        Generate hypotheticals for a decomposed legal issue.

        Uses the primary question and search queries to generate
        diverse hypotheticals.

        Args:
            issue: Decomposed legal issue dict
            num_hypotheticals: Number of hypotheticals per query

        Returns:
            Tuple of (list of hypotheticals, total latency in ms)
        """
        all_hypotheticals = []
        total_latency = 0

        # Get the primary question
        primary_question = issue.get("primary_question", "")
        if primary_question:
            hypos, latency = await self.generate_multiple_hypotheticals(
                primary_question,
                num_hypotheticals=num_hypotheticals
            )
            all_hypotheticals.extend(hypos)
            total_latency += latency

        # Also use Arabic search queries if available
        search_queries_ar = issue.get("search_queries_ar", [])
        for query in search_queries_ar[:2]:  # Limit to first 2 queries
            if query and query != primary_question:
                hypo, latency = await self.generate_hypothetical(query)
                if hypo:
                    all_hypotheticals.append(hypo)
                total_latency += latency

        # Deduplicate
        seen = set()
        unique_hypotheticals = []
        for h in all_hypotheticals:
            # Use first 100 chars as key
            key = h[:100]
            if key not in seen:
                seen.add(key)
                unique_hypotheticals.append(h)

        return unique_hypotheticals, total_latency
