"""
Decomposer Component - Breaks Legal Brief into legal sub-issues for research.
"""
import json
from typing import TYPE_CHECKING

from agentex.lib.utils.logging import make_logger

if TYPE_CHECKING:
    from project.llm_client import LegalSearchLLMClient

logger = make_logger(__name__)


DECOMPOSE_SYSTEM_PROMPT_AR = """You are a Qatari legal analyst specializing in Power of Attorney (POA) law under the laws of the State of Qatar.

⚖️ LEGAL FRAMEWORK: QATARI LAW EXCLUSIVELY
- All analysis must be based on Qatari law (Civil Code, Notarization Law, Commercial Companies Law, etc.)
- Regardless of the nationalities of parties, Qatari law applies to all transactions in Qatar
- The legal corpus is from Qatar's Al Meezan legal portal
- Do NOT reference foreign legal systems - only Qatari law applies

Your task is to analyze a Legal Brief and decompose it into specific legal sub-issues that need research under Qatari law.

For each issue, you should:
1. Identify the legal category (grantor_capacity, agent_capacity, poa_scope, substitution_rights, formalities, validity, compliance, business_rules)
2. Formulate a clear primary legal question under Qatari law
3. Generate sub-questions that help answer the main question
4. Generate search queries in ARABIC to find relevant Qatari legal articles (the legal corpus is in Arabic)

Focus especially on AUTHORITY SCOPE issues - when a grantor with limited authority tries to grant broader powers.

Return your analysis as a JSON array of issues."""


DECOMPOSE_SYSTEM_PROMPT_EN = """You are a Qatari legal analyst specializing in Power of Attorney (POA) law under the laws of the State of Qatar.

⚖️ LEGAL FRAMEWORK: QATARI LAW EXCLUSIVELY
- All analysis must be based on Qatari law (Civil Code, Notarization Law, Commercial Companies Law, etc.)
- Regardless of the nationalities of parties, Qatari law applies to all transactions in Qatar
- The legal corpus is from Qatar's Al Meezan legal portal
- Do NOT reference foreign legal systems - only Qatari law applies

Your task is to analyze a Legal Brief and decompose it into specific legal sub-issues that need research under Qatari law.

For each issue, you should:
1. Identify the legal category (grantor_capacity, agent_capacity, poa_scope, substitution_rights, formalities, validity, compliance, business_rules)
2. Formulate a clear primary legal question under Qatari law
3. Generate sub-questions that help answer the main question
4. Generate search queries in ARABIC to find relevant Qatari legal articles (the legal corpus is in Arabic)

Focus especially on AUTHORITY SCOPE issues - when a grantor with limited authority tries to grant broader powers.

Return your analysis as a JSON array of issues."""


DECOMPOSE_PROMPT_TEMPLATE_AR = """Analyze this Legal Brief and decompose it into legal sub-issues that need research.

## LEGAL BRIEF:
{legal_brief}

---

Based on the discrepancies and open questions in this brief, generate a list of legal issues to research.

Each issue should follow this structure:
{{
    "issue_id": "ISSUE_1",
    "category": "grantor_capacity|agent_capacity|poa_scope|substitution_rights|formalities|validity|compliance|business_rules",
    "primary_question": "السؤال القانوني الرئيسي (بالعربية)",
    "sub_questions": ["أسئلة فرعية تساعد في الإجابة على السؤال الرئيسي (بالعربية)"],
    "relevant_facts": ["Facts from the brief relevant to this issue"],
    "search_queries_ar": ["Search queries IN ARABIC to find relevant legal articles - use formal legal Arabic terminology"],
    "priority": 1-3 (1 = highest priority)
}}

IMPORTANT: Focus on the KEY LEGAL ISSUE here:
- If the grantor has LIMITED authority (e.g., "Passports only") but is trying to grant BROADER powers (e.g., "full management"), this is the CRITICAL issue
- Research: Can a principal delegate authority they don't possess?
- Research: What happens when POA scope exceeds grantor's authority?

LANGUAGE: ALL text values (primary_question, sub_questions, relevant_facts) MUST be in Arabic. JSON keys and category values remain in English.

Return ONLY a JSON array of issues, no additional text.

Example output:
[
    {{
        "issue_id": "ISSUE_1",
        "category": "grantor_capacity",
        "primary_question": "هل يملك الموكل صلاحية كافية لتفويض الصلاحيات المحددة في هذا التوكيل؟",
        "sub_questions": [
            "ما هو نطاق صلاحيات الموكل حسب السجل التجاري؟",
            "هل يمكن لمدير ذو صلاحية محدودة تفويض صلاحيات تتجاوز نطاقه؟"
        ],
        "relevant_facts": ["الموكل مدير (جوازات سفر فقط)", "التوكيل يمنح صلاحيات إدارة كاملة"],
        "search_queries_ar": ["لا يجوز للموكل أن يمنح الوكيل صلاحيات تزيد عما يملكه", "حدود الوكالة", "تجاوز صلاحيات الموكل", "أهلية الموكل في الوكالة"],
        "priority": 1
    }}
]"""


DECOMPOSE_PROMPT_TEMPLATE_EN = """Analyze this Legal Brief and decompose it into legal sub-issues that need research.

## LEGAL BRIEF:
{legal_brief}

---

Based on the discrepancies and open questions in this brief, generate a list of legal issues to research.

Each issue should follow this structure:
{{
    "issue_id": "ISSUE_1",
    "category": "grantor_capacity|agent_capacity|poa_scope|substitution_rights|formalities|validity|compliance|business_rules",
    "primary_question": "The main legal question in English",
    "sub_questions": ["Sub-questions that help answer the main question, in English"],
    "relevant_facts": ["Facts from the brief relevant to this issue, in English"],
    "search_queries_ar": ["Search queries IN ARABIC to find relevant legal articles - use formal legal Arabic terminology"],
    "priority": 1-3 (1 = highest priority)
}}

IMPORTANT: Focus on the KEY LEGAL ISSUE here:
- If the grantor has LIMITED authority (e.g., "Passports only") but is trying to grant BROADER powers (e.g., "full management"), this is the CRITICAL issue
- Research: Can a principal delegate authority they don't possess?
- Research: What happens when POA scope exceeds grantor's authority?

LANGUAGE:
- primary_question, sub_questions, relevant_facts: MUST be in English
- search_queries_ar: MUST ALWAYS be in Arabic (legal corpus is Arabic)
- JSON keys and category values remain in English

Return ONLY a JSON array of issues, no additional text.

Example output:
[
    {{
        "issue_id": "ISSUE_1",
        "category": "grantor_capacity",
        "primary_question": "Does the grantor have sufficient authority to delegate the powers specified in this POA?",
        "sub_questions": [
            "What is the scope of the grantor's authority per the commercial registration?",
            "Can a manager with limited authority delegate powers beyond their scope?"
        ],
        "relevant_facts": ["The grantor is a manager (passports only)", "The POA grants full management powers"],
        "search_queries_ar": ["لا يجوز للموكل أن يمنح الوكيل صلاحيات تزيد عما يملكه", "حدود الوكالة", "تجاوز صلاحيات الموكل", "أهلية الموكل في الوكالة"],
        "priority": 1
    }}
]"""


class Decomposer:
    """Decomposes Legal Brief into legal sub-issues for research."""

    def __init__(self, llm_client: "LegalSearchLLMClient"):
        self.llm = llm_client

    async def decompose(self, legal_brief: dict, locale: str = "ar") -> list[dict]:
        """
        Decompose a Legal Brief into legal sub-issues.

        Args:
            legal_brief: The Legal Brief from the Condenser Agent
            locale: Language locale ("ar" or "en") - defaults to "ar"

        Returns:
            List of legal issues to research
        """
        # Select prompts based on locale
        system_prompt = DECOMPOSE_SYSTEM_PROMPT_EN if locale == "en" else DECOMPOSE_SYSTEM_PROMPT_AR
        prompt_template = DECOMPOSE_PROMPT_TEMPLATE_EN if locale == "en" else DECOMPOSE_PROMPT_TEMPLATE_AR

        prompt = prompt_template.format(
            legal_brief=json.dumps(legal_brief, ensure_ascii=False, indent=2)
        )

        logger.info(f"Calling LLM to decompose legal brief (locale={locale})...")

        response = await self.llm.chat(
            user_message=prompt,
            system_message=system_prompt,
            temperature=0.2
        )

        # Parse the response
        try:
            # Clean up response
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]

            issues = json.loads(clean_response.strip())

            # Validate structure
            for issue in issues:
                if "issue_id" not in issue:
                    issue["issue_id"] = f"ISSUE_{issues.index(issue) + 1}"
                if "priority" not in issue:
                    issue["priority"] = 2
                # Handle Arabic search queries - use search_queries_ar if available, fallback to search_queries
                if "search_queries_ar" not in issue and "search_queries" not in issue:
                    issue["search_queries_ar"] = [issue.get("primary_question", "")]
                elif "search_queries_ar" not in issue:
                    # Fallback: use English queries if Arabic not provided
                    issue["search_queries_ar"] = issue.get("search_queries", [])

            # Sort by priority
            issues.sort(key=lambda x: x.get("priority", 2))

            logger.info(f"Decomposed into {len(issues)} issues")
            return issues

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decomposition response: {e}")
            # Return a default issue based on the open questions
            open_questions = legal_brief.get("open_questions", [])
            if open_questions:
                return [
                    {
                        "issue_id": f"ISSUE_{i+1}",
                        "category": q.get("category", "compliance"),
                        "primary_question": q.get("question", ""),
                        "sub_questions": [],
                        "relevant_facts": q.get("relevant_facts", []),
                        "search_queries": [q.get("question", "")],
                        "priority": 1 if q.get("priority") == "critical" else 2
                    }
                    for i, q in enumerate(open_questions)
                ]
            return []
