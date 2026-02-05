"""
Synthesizer Component - Generates legal opinion from evidence.
"""
import json
from typing import TYPE_CHECKING

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient

logger = make_logger(__name__)


SYNTHESIS_SYSTEM_PROMPT_AR = """أنت محلل قانوني أول تُنتج آراء قانونية مفصلة لطلبات التوثيق.

مهمتك:
1. تحليل كل مسألة قانونية محددة
2. تطبيق المواد القانونية ذات الصلة على الحقائق
3. إنتاج رأي قانوني شامل ومُحكم
4. الاستشهاد بمواد محددة مع اقتباسات دقيقة لدعم كل استنتاج

هيكل الرأي:
- ابدأ بملخص واضح للقضية
- عالج كل مسألة قانونية بتحليل مفصل
- قدّم استشهادات واضحة بأرقام المواد والنص ذي الصلة
- أعطِ قراراً نهائياً مع التسبيب

متطلبات الاستشهاد:
- كل استنتاج قانوني يجب أن يستشهد بمادة/مواد محددة
- اقتبس الجزء ذي الصلة من المادة
- اشرح كيف تنطبق المادة على الحقائق المحددة

متطلبات اللغة الصارمة:
- ⚠️ جميع القيم النصية في مخرجات JSON يجب أن تكون بالعربية بالكامل.
- لا تكتب أي كلمة إنجليزية في القيم النصية إطلاقاً.
- اكتب ملخصات الرأي والتحليل والتسبيب والملاحظات والتوصيات والشروط بالعربية.
- opinion_summary_ar: الملخص العربي (الأساسي والأكثر تفصيلاً).
- opinion_summary_en: ملخص مختصر بالإنجليزية.
- نصوص المواد القانونية (article_text, quoted_text): اكتبها بالعربية. إذا كان النص الأصلي بالإنجليزية، ترجمه للعربية.
- مفاتيح JSON تبقى بالإنجليزية (مثل "case_summary", "overall_finding").
- القيم الثابتة فقط تبقى بالإنجليزية: VALID, INVALID, SUPPORTED, NOT_SUPPORTED, PARTIALLY_SUPPORTED, UNCLEAR, HIGH, MEDIUM, LOW, ISSUE_1, C1.

سيراجع رأيك متخصصون قانونيون. كن شاملاً ودقيقاً ومُحكماً."""


SYNTHESIS_SYSTEM_PROMPT_EN = """You are a senior legal analyst producing detailed legal opinions for notarization requests.

Your task:
1. Analyze each identified legal issue
2. Apply relevant legal articles to the facts
3. Produce a comprehensive, well-reasoned legal opinion
4. Cite specific articles with accurate quotes to support each conclusion

Opinion structure:
- Start with a clear case summary
- Address each legal issue with detailed analysis
- Provide clear citations with article numbers and relevant text
- Give a final decision with reasoning

Citation requirements:
- Every legal conclusion must cite specific article(s)
- Quote the relevant portion of the article
- Explain how the article applies to the specific facts

Strict language requirements:
- ⚠️ All text values in JSON output must be entirely in English.
- Do not write any Arabic words in text values.
- Write opinion summaries, analysis, reasoning, notes, recommendations, and conditions in English.
- opinion_summary_en: The English summary (primary and most detailed).
- opinion_summary_ar: A brief summary in Arabic.
- Legal article texts (article_text, quoted_text): Write them in English. If the original text is in Arabic, translate it to English.
- JSON keys remain in English (e.g., "case_summary", "overall_finding").
- Only constant values remain in English: VALID, INVALID, SUPPORTED, NOT_SUPPORTED, PARTIALLY_SUPPORTED, UNCLEAR, HIGH, MEDIUM, LOW, ISSUE_1, C1.

Your opinion will be reviewed by legal professionals. Be thorough, precise, and well-reasoned."""


SYNTHESIS_PROMPT_TEMPLATE_AR = """أنتج رأياً قانونياً شاملاً بناءً على حقائق القضية والبحث القانوني التالي.

## الموجز القانوني (حقائق القضية):
{legal_brief}

## المسائل القانونية للتحليل:
{issues}

## المواد القانونية ذات الصلة:
{articles}

## الأدلة المسترجعة لكل مسألة:
{issue_evidence}

---

⚠️ تنبيه صارم جداً: جميع القيم النصية يجب أن تكون بالعربية فقط. لا تستخدم الإنجليزية إطلاقاً في القيم النصية.
- نصوص المواد القانونية: اكتبها بالعربية (ترجم من الإنجليزية إذا لزم الأمر).
- القيم الثابتة فقط بالإنجليزية: VALID, INVALID, SUPPORTED, NOT_SUPPORTED, PARTIALLY_SUPPORTED, UNCLEAR, HIGH, MEDIUM, LOW.

أنتج رأياً قانونياً مفصلاً بالهيكل التالي:

{{
    "case_summary": {{
        "application_type": "نوع الطلب بالعربية مثل: توكيل خاص لشركة",
        "parties_involved": "وصف مختصر للأطراف بالعربية",
        "core_question": "السؤال القانوني الرئيسي بالعربية",
        "key_facts": ["الحقائق الأهم بالعربية"]
    }},
    "overall_finding": "VALID|INVALID|VALID_WITH_CONDITIONS|REQUIRES_REVIEW|INCONCLUSIVE",
    "confidence_score": 0.85,
    "confidence_level": "HIGH|MEDIUM|LOW",
    "decision_bucket": "valid|valid_with_remediations|invalid|needs_review",
    "opinion_summary_en": "ملخص مختصر بالإنجليزية فقط",
    "opinion_summary_ar": "ملخص الرأي القانوني بالعربية - 2-3 فقرات مفصلة. هذا هو الملخص الأساسي.",
    "detailed_analysis": {{
        "introduction": "مقدمة التحليل القانوني بالعربية",
        "issue_by_issue_analysis": [
            {{
                "issue_id": "ISSUE_1",
                "issue_title": "عنوان المسألة بالعربية مثل: نطاق صلاحيات الموكّل",
                "category": "الصفة أو الصلاحية أو النطاق أو الشكليات أو الصلاحية أو الامتثال",
                "facts_considered": ["الحقائق ذات الصلة بالعربية"],
                "legal_analysis": "فقرة مفصلة تشرح التسبيب القانوني بالعربية",
                "applicable_articles": [
                    {{
                        "article_number": 2,
                        "article_text": "نص المادة بالعربية - لا يجوز للموكل أن يمنح الوكيل حقوقاً تزيد عما يملكه",
                        "application_to_facts": "كيف تنطبق هذه المادة على الحقائق المحددة بالعربية"
                    }}
                ],
                "finding": "SUPPORTED|NOT_SUPPORTED|PARTIALLY_SUPPORTED|UNCLEAR",
                "confidence": 0.90,
                "reasoning_summary": "ملخص الاستنتاج بجملة واحدة بالعربية"
            }}
        ],
        "synthesis": "كيف تتضافر النتائج الفردية لتشكيل الاستنتاج العام بالعربية",
        "conclusion": "القرار النهائي مع التسبيب الواضح بالعربية"
    }},
    "citations": [
        {{
            "citation_id": "C1",
            "article_number": 2,
            "law_name": "اسم القانون بالعربية",
            "chapter": "الفصل أو القسم بالعربية",
            "quoted_text": "نص المادة المقتبس بالعربية",
            "relevance": "سبب أهمية هذا الاستشهاد بالعربية"
        }}
    ],
    "concerns": ["الملاحظات المحددة بالعربية"],
    "recommendations": ["التوصيات المحددة بالعربية"],
    "conditions": ["الشروط المحددة بالعربية إذا كان القرار صالح مع تصحيحات"],
    "grounding_score": 0.85
}}

تعليمات مهمة:
1. اقتبس بدقة - اقتبس النص الفعلي من المواد بالعربية
2. كن محدداً - أشر إلى حقائق محددة من القضية
3. أظهر التسبيب - اشرح كيف تنطبق كل مادة على الحقائق
4. كن شاملاً - عالج كل مسألة محددة
5. كن موضوعياً - قدّم التحليل القانوني دون تحيز
6. ⚠️ جميع القيم النصية بالعربية فقط. مفاتيح JSON والقيم الثابتة (VALID, INVALID, SUPPORTED, الخ) فقط بالإنجليزية.

أعد فقط كائن JSON."""


SYNTHESIS_PROMPT_TEMPLATE_EN = """Produce a comprehensive legal opinion based on the following case facts and legal research.

## Legal Brief (Case Facts):
{legal_brief}

## Legal Issues for Analysis:
{issues}

## Relevant Legal Articles:
{articles}

## Retrieved Evidence per Issue:
{issue_evidence}

---

⚠️ Strict requirement: All text values must be in English only. Do not use Arabic in text values.
- Legal article texts: Write them in English (translate from Arabic if needed).
- Only constant values in English: VALID, INVALID, SUPPORTED, NOT_SUPPORTED, PARTIALLY_SUPPORTED, UNCLEAR, HIGH, MEDIUM, LOW.

Produce a detailed legal opinion with the following structure:

{{
    "case_summary": {{
        "application_type": "Application type e.g.: Special POA for Company",
        "parties_involved": "Brief description of parties",
        "core_question": "The main legal question",
        "key_facts": ["Most important facts"]
    }},
    "overall_finding": "VALID|INVALID|VALID_WITH_CONDITIONS|REQUIRES_REVIEW|INCONCLUSIVE",
    "confidence_score": 0.85,
    "confidence_level": "HIGH|MEDIUM|LOW",
    "decision_bucket": "valid|valid_with_remediations|invalid|needs_review",
    "opinion_summary_en": "Detailed English opinion summary - 2-3 paragraphs. This is the primary summary.",
    "opinion_summary_ar": "Brief Arabic summary only",
    "detailed_analysis": {{
        "introduction": "Legal analysis introduction",
        "issue_by_issue_analysis": [
            {{
                "issue_id": "ISSUE_1",
                "issue_title": "Issue title e.g.: Scope of Grantor's Authority",
                "category": "capacity or authority or scope or formalities or validity or compliance",
                "facts_considered": ["Relevant facts"],
                "legal_analysis": "Detailed paragraph explaining legal reasoning",
                "applicable_articles": [
                    {{
                        "article_number": 2,
                        "article_text": "Article text in English - A principal may not grant the agent rights exceeding what they possess",
                        "application_to_facts": "How this article applies to the specific facts"
                    }}
                ],
                "finding": "SUPPORTED|NOT_SUPPORTED|PARTIALLY_SUPPORTED|UNCLEAR",
                "confidence": 0.90,
                "reasoning_summary": "One-sentence conclusion summary"
            }}
        ],
        "synthesis": "How individual findings combine to form the overall conclusion",
        "conclusion": "Final decision with clear reasoning"
    }},
    "citations": [
        {{
            "citation_id": "C1",
            "article_number": 2,
            "law_name": "Law name in English",
            "chapter": "Chapter or section in English",
            "quoted_text": "Quoted article text in English",
            "relevance": "Why this citation is important"
        }}
    ],
    "concerns": ["Specific concerns"],
    "recommendations": ["Specific recommendations"],
    "conditions": ["Specific conditions if decision is valid with remediations"],
    "grounding_score": 0.85
}}

Important instructions:
1. Cite precisely - quote actual text from articles in English
2. Be specific - refer to specific facts from the case
3. Show reasoning - explain how each article applies to the facts
4. Be comprehensive - address every identified issue
5. Be objective - present legal analysis without bias
6. ⚠️ All text values in English only. JSON keys and constant values (VALID, INVALID, SUPPORTED, etc.) only in English.

Return ONLY a JSON object."""


class Synthesizer:
    """Synthesizes legal opinion from Legal Brief and retrieved evidence."""

    def __init__(self, llm_client: "LegalSearchLLMClient"):
        self.llm = llm_client

    async def synthesize(
        self,
        legal_brief: dict,
        issues: list[dict],
        issue_evidence: dict[str, list[dict]],
        all_articles: list[dict],
        locale: str = "ar"
    ) -> dict:
        """
        Synthesize a legal opinion from the evidence.

        Args:
            legal_brief: The Legal Brief
            issues: List of legal issues analyzed
            issue_evidence: Map of issue_id -> relevant articles
            all_articles: All unique articles retrieved
            locale: Language locale ("ar" or "en") - defaults to "ar"

        Returns:
            Legal opinion dict
        """
        # Select prompts based on locale
        system_prompt = SYNTHESIS_SYSTEM_PROMPT_EN if locale == "en" else SYNTHESIS_SYSTEM_PROMPT_AR
        prompt_template = SYNTHESIS_PROMPT_TEMPLATE_EN if locale == "en" else SYNTHESIS_PROMPT_TEMPLATE_AR

        # Format articles for prompt
        articles_text = self._format_articles(all_articles)
        evidence_text = self._format_issue_evidence(issue_evidence)

        prompt = prompt_template.format(
            legal_brief=json.dumps(legal_brief, ensure_ascii=False, indent=2),
            issues=json.dumps(issues, ensure_ascii=False, indent=2),
            articles=articles_text,
            issue_evidence=evidence_text
        )

        logger.info(f"Calling LLM to synthesize legal opinion (locale={locale})...")

        response = await self.llm.chat(
            user_message=prompt,
            system_message=system_prompt,
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
        """Format articles for the prompt, preferring Arabic text."""
        if not articles:
            return "لم يتم العثور على مواد ذات صلة."

        lines = []
        for art in articles:
            lines.append(f"### مادة {art.get('article_number', '?')}")
            if art.get("law_name"):
                lines.append(f"القانون: {art.get('law_name')}")

            text_ar = art.get("text_arabic") or art.get("text_ar", "")
            text_en = art.get("text_english") or art.get("text_en", "")

            # Prefer Arabic text; fall back to English
            if text_ar:
                lines.append(f"النص: {text_ar}")
            elif text_en:
                lines.append(f"النص (إنجليزي - يرجى ترجمته للعربية في المخرجات): {text_en}")

            lines.append(f"التشابه: {art.get('similarity', 0):.0%}")
            lines.append("")

        return "\n".join(lines)

    def _format_issue_evidence(self, issue_evidence: dict[str, list[dict]]) -> str:
        """Format issue evidence for the prompt."""
        lines = []
        for issue_id, articles in issue_evidence.items():
            lines.append(f"### {issue_id}")
            if articles:
                for art in articles:
                    lines.append(f"- مادة {art.get('article_number')}: {art.get('similarity', 0):.0%}")
            else:
                lines.append("- لم يتم العثور على مواد ذات صلة")
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
