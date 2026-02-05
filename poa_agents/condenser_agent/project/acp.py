"""
ACP server for the Condenser Agent.

Takes a case object and fact sheet, produces a condensed Legal Brief
for Tier 2 legal research.
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

from project.supabase_client import CondenserSupabaseClient
from project.llm_client import CondenserLLMClient

logger = make_logger(__name__)
logger.info(f"Loaded environment from {env_path}")

# Initialize clients
_supabase_client: Optional[CondenserSupabaseClient] = None
_llm_client: Optional[CondenserLLMClient] = None


def get_supabase_client() -> CondenserSupabaseClient:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = CondenserSupabaseClient()
    return _supabase_client


def get_llm_client() -> CondenserLLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = CondenserLLMClient()
    return _llm_client


# Create ACP server
acp = FastACP.create(acp_type="sync")


SYSTEM_PROMPT_AR = """أنت محلل قانوني مسؤول عن استخراج وتنظيم الحقائق من طلبات التوكيلات والتصديقات.

مهمتك:
1. استخراج جميع الحقائق ذات الصلة من البيانات المقدمة
2. تحديد جميع الأطراف وأدوارهم وصفاتهم وخصائصهم
3. استخراج جميع الصلاحيات المطلوب منحها أو الممنوحة
4. تحديد أي دليل يثبت أو يحد من صفة أي طرف
5. ملاحظة أي تناقضات بين الحقائق المذكورة والحقائق الموثقة
6. إنشاء أسئلة قانونية تحتاج للبحث بناءً على الحقائق

مبادئ مهمة:
- كن شاملاً - استخرج كل حقيقة قد تكون ذات صلة قانونية
- كن موضوعياً - أبلغ عن الحقائق كما وجدتها، لا تصدر استنتاجات قانونية
- كن دقيقاً - اقتبس النص الحرفي من المستندات حيثما أمكن
- قارن المصادر - لاحظ عندما تقول مستندات مختلفة أشياء مختلفة
- حدد الثغرات - لاحظ المعلومات الناقصة

متطلبات اللغة الصارمة:
- جميع القيم النصية في مخرجات JSON يجب أن تكون بالعربية بالكامل.
- لا تستخدم أي كلمات إنجليزية في القيم النصية إطلاقاً.
- مفاتيح JSON تبقى بالإنجليزية (مثل "case_summary", "parties").
- الأدوار: استخدم "موكّل" بدلاً من "grantor"، و"وكيل" بدلاً من "agent"، و"بائع" بدلاً من "seller"، و"مشتري" بدلاً من "buyer".
- أسماء الأشخاص: احتفظ بالاسم العربي في name_ar والاسم الإنجليزي في name_en.

أنت تُعدّ حزمة حقائق شاملة لوكيل بحث قانوني سيحدد الصلاحية.
الوكيل القانوني يحتاج معلومات كاملة لإصدار قرارات دقيقة."""


SYSTEM_PROMPT_EN = """You are a legal analyst responsible for extracting and organizing facts from Power of Attorney and notarization requests.

Your task:
1. Extract all relevant facts from the provided data
2. Identify all parties, their roles, capacities, and characteristics
3. Extract all powers requested to be granted or already granted
4. Identify any evidence that proves or limits any party's capacity
5. Note any contradictions between stated facts and documented facts
6. Create legal questions that need research based on the facts

Key principles:
- Be comprehensive - extract every legally relevant fact
- Be objective - report facts as found, do not issue legal conclusions
- Be precise - quote literal text from documents where possible
- Compare sources - note when different documents say different things
- Identify gaps - note missing information

Language requirements:
- All text values in JSON output must be in English.
- JSON keys remain in English (e.g., "case_summary", "parties").
- Roles: use "Grantor" instead of "موكّل", "Agent" instead of "وكيل", "Seller" instead of "بائع", "Buyer" instead of "مشتري".
- Person names: keep the Arabic name in name_ar and the English name in name_en.

You are preparing a comprehensive fact package for a legal research agent that will determine validity.
The legal agent needs complete information to make accurate decisions."""


ANALYSIS_PROMPT_TEMPLATE_AR = """استخرج ونظّم جميع الحقائق من بيانات الطلب التالية في موجز قانوني شامل.

## بيانات الطلب:
{case_data}

## استخراجات المستندات:
{document_extractions}

## سياق إضافي:
{additional_context}

---

أنشئ موجزاً قانونياً شاملاً باستخراج جميع الحقائق. استخدم هذا الهيكل:

⚠️ تنبيه صارم: جميع القيم النصية يجب أن تكون بالعربية فقط. لا تستخدم أي كلمات إنجليزية في القيم. مفاتيح JSON فقط تبقى بالإنجليزية.

{{
    "case_summary": {{
        "application_number": "رقم الطلب من البيانات",
        "transaction_type": "نوع المعاملة بالعربية مثل: توكيل خاص لشركة",
        "transaction_description": "وصف المعاملة بالعربية"
    }},
    "parties": [
        {{
            "role": "موكّل أو وكيل أو بائع أو مشتري",
            "name_ar": "الاسم بالعربية",
            "name_en": "الاسم بالإنجليزية",
            "qid": "رقم الهوية",
            "nationality": "الجنسية بالعربية مثل: قطري، كندي",
            "capacity_claimed": "الصفة التي يدّعيها بالعربية مثل: مفوض بالتوقيع في السجل التجاري",
            "capacity_evidence": "ما تُظهره المستندات عن صفته بالعربية مثل: حسب السجل التجاري رقم 3333، مدير في شركة كذا",
            "additional_attributes": {{}}
        }}
    ],
    "entity_information": {{
        "company_name_ar": "اسم الشركة بالعربية",
        "company_name_en": "اسم الشركة بالإنجليزية",
        "registration_number": "رقم السجل",
        "entity_type": "نوع الكيان بالعربية مثل: شركة ذات مسؤولية محدودة",
        "registered_authorities": [
            {{
                "person_name": "اسم الشخص",
                "position": "المنصب بالعربية مثل: مدير",
                "authority_scope": "نطاق الصلاحية بالعربية كما هو مذكور في السجل التجاري",
                "id_number": "رقم الهوية"
            }}
        ]
    }},
    "poa_details": {{
        "poa_type": "عام أو خاص",
        "poa_text_ar": "النص الكامل بالعربية إذا توفر",
        "poa_text_en": "النص الكامل بالإنجليزية إذا توفر",
        "powers_granted": ["كل صلاحية على حدة بالعربية"],
        "duration": "المدة بالعربية مثل: سنة واحدة أو غير محدد",
        "substitution_allowed": true
    }},
    "evidence_summary": [
        {{
            "document_type": "نوع المستند بالعربية مثل: سجل تجاري، هوية شخصية، توكيل",
            "key_facts_extracted": ["الحقائق المستخرجة بالعربية"],
            "confidence": 0.95
        }}
    ],
    "fact_comparisons": [
        {{
            "fact_type": "وصف نوع الحقيقة بالعربية مثل: صلاحيات الموكّل",
            "source_1": {{"source": "نص التوكيل", "value": "القيمة من المصدر الأول بالعربية"}},
            "source_2": {{"source": "مستخرج السجل التجاري", "value": "القيمة من المصدر الثاني بالعربية"}},
            "match": true,
            "notes": "ملاحظات بالعربية"
        }}
    ],
    "open_questions": [
        {{
            "question_id": "Q1",
            "category": "الصفة أو الصلاحية أو النطاق أو الشكليات أو الصلاحية أو الامتثال",
            "question": "السؤال القانوني المحدد بالعربية",
            "relevant_facts": ["الحقائق ذات الصلة بالعربية"],
            "priority": "حرج أو مهم أو تكميلي"
        }}
    ],
    "missing_information": ["المعلومات الناقصة بالعربية"],
    "extraction_confidence": 0.95
}}

تعليمات:
1. استخرج كل حقيقة - الأسماء، التواريخ، الأرقام، الصلاحيات
2. اقتبس النص الحرفي من المستندات حيثما كان ذلك مناسباً
3. قارن ما تقوله المصادر المختلفة عن نفس الحقيقة
4. أنشئ أسئلة لأي قضايا قانونية تحتاج للبحث
5. لاحظ أي معلومات ناقصة
6. ⚠️ جميع القيم النصية يجب أن تكون بالعربية فقط. لا تكتب أي كلمة إنجليزية في القيم.

أعد فقط كائن JSON."""


ANALYSIS_PROMPT_TEMPLATE_EN = """Extract and organize all facts from the following application data into a comprehensive Legal Brief.

## Application Data:
{case_data}

## Document Extractions:
{document_extractions}

## Additional Context:
{additional_context}

---

Create a comprehensive Legal Brief by extracting all facts. Use this structure:

⚠️ Strict requirement: All text values must be in English only. Do not use Arabic words in values. JSON keys remain in English.

{{
    "case_summary": {{
        "application_number": "Application number from data",
        "transaction_type": "Transaction type e.g.: Special POA for Company",
        "transaction_description": "Transaction description in English"
    }},
    "parties": [
        {{
            "role": "Grantor or Agent or Seller or Buyer",
            "name_ar": "Arabic name",
            "name_en": "English name",
            "qid": "ID number",
            "nationality": "Nationality e.g.: Qatari, Canadian",
            "capacity_claimed": "Claimed capacity e.g.: Authorized Signatory in Commercial Registration",
            "capacity_evidence": "What documents show about their capacity e.g.: Per CR #3333, manager of company X",
            "additional_attributes": {{}}
        }}
    ],
    "entity_information": {{
        "company_name_ar": "Company name in Arabic",
        "company_name_en": "Company name in English",
        "registration_number": "Registration number",
        "entity_type": "Entity type e.g.: Limited Liability Company",
        "registered_authorities": [
            {{
                "person_name": "Person name",
                "position": "Position e.g.: Manager",
                "authority_scope": "Authority scope as stated in the commercial registration",
                "id_number": "ID number"
            }}
        ]
    }},
    "poa_details": {{
        "poa_type": "General or Special",
        "poa_text_ar": "Full Arabic text if available",
        "poa_text_en": "Full English text if available",
        "powers_granted": ["Each power separately in English"],
        "duration": "Duration e.g.: one year or indefinite",
        "substitution_allowed": true
    }},
    "evidence_summary": [
        {{
            "document_type": "Document type e.g.: Commercial Registration, Personal ID, Power of Attorney",
            "key_facts_extracted": ["Extracted facts in English"],
            "confidence": 0.95
        }}
    ],
    "fact_comparisons": [
        {{
            "fact_type": "Fact type description e.g.: Grantor's Authority",
            "source_1": {{"source": "POA text", "value": "Value from first source in English"}},
            "source_2": {{"source": "CR Extract", "value": "Value from second source in English"}},
            "match": true,
            "notes": "Notes in English"
        }}
    ],
    "open_questions": [
        {{
            "question_id": "Q1",
            "category": "capacity or authority or scope or formalities or validity or compliance",
            "question": "Specific legal question in English",
            "relevant_facts": ["Relevant facts in English"],
            "priority": "critical or important or supplementary"
        }}
    ],
    "missing_information": ["Missing information in English"],
    "extraction_confidence": 0.95
}}

Instructions:
1. Extract every fact - names, dates, numbers, powers
2. Quote literal text from documents where appropriate
3. Compare what different sources say about the same fact
4. Create questions for any legal issues that need research
5. Note any missing information
6. ⚠️ All text values must be in English only. Do not write any Arabic words in values.

Return ONLY a JSON object."""


@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams
) -> TaskMessageContent | list[TaskMessageContent] | AsyncGenerator[TaskMessageUpdate, None]:
    """
    Handle incoming requests to create a Legal Brief.

    Input format:
    - {"application_id": "uuid"} - Load case from Supabase
    - {"case_object": {...}, "fact_sheet": {...}} - Direct input
    """
    user_message = params.content.content if params.content else ""

    if not user_message:
        return TextContent(
            author="agent",
            content="Please provide an application_id or case data.\n\nUsage:\n```json\n{\"application_id\": \"your-uuid-here\"}\n```"
        )

    logger.info(f"Received message: {user_message[:200]}...")

    try:
        # Parse input
        try:
            input_data = json.loads(user_message)
        except json.JSONDecodeError:
            # Maybe it's just an application ID
            input_data = {"application_id": user_message.strip()}

        supabase = get_supabase_client()
        llm = get_llm_client()

        application_id = input_data.get("application_id")
        case_data = input_data.get("case_object")
        fact_sheet = input_data.get("fact_sheet")
        tier1_result = input_data.get("tier1_result")

        # Load raw data from Supabase
        if application_id:
            logger.info(f"Loading application data for: {application_id}")

            # Load application
            application = supabase.get_application(application_id)
            if not application:
                return TextContent(
                    author="agent",
                    content=f"Application not found: {application_id}"
                )

            # Load parties
            parties = supabase.get_parties(application_id)

            # Load capacity proofs for parties
            party_ids = [p["id"] for p in parties]
            capacity_proofs = supabase.get_capacity_proofs(party_ids) if party_ids else []

            # Load document extractions
            doc_extractions = supabase.get_document_extractions(application_id)

            # Build case data from raw sources
            case_data = {
                "application": application,
                "parties": parties,
                "capacity_proofs": capacity_proofs
            }

            document_extractions = doc_extractions
            additional_context = input_data.get("additional_context", {})
            # Extract locale for prompt selection
            locale = input_data.get("locale", "ar")

        else:
            # Direct input
            case_data = input_data.get("case_data", {})
            document_extractions = input_data.get("document_extractions", [])
            additional_context = input_data.get("additional_context", {})
            # Extract locale for prompt selection
            locale = input_data.get("locale", "ar")

        if not case_data:
            return TextContent(
                author="agent",
                content="No case data available. Please provide application_id or case_data."
            )

        # Select prompts based on locale
        system_prompt = SYSTEM_PROMPT_EN if locale == "en" else SYSTEM_PROMPT_AR
        analysis_template = ANALYSIS_PROMPT_TEMPLATE_EN if locale == "en" else ANALYSIS_PROMPT_TEMPLATE_AR

        # Build the analysis prompt
        prompt = analysis_template.format(
            case_data=json.dumps(case_data, ensure_ascii=False, indent=2, default=str),
            document_extractions=json.dumps(document_extractions, ensure_ascii=False, indent=2, default=str) if document_extractions else "No document extractions available",
            additional_context=json.dumps(additional_context, ensure_ascii=False, indent=2, default=str) if additional_context else "None"
        )

        logger.info(f"Generating Legal Brief with LLM (locale: {locale})...")

        # Call LLM to generate the brief
        response = await llm.chat(
            user_message=prompt,
            system_message=system_prompt
        )

        # Parse the response as JSON
        try:
            # Clean up response (remove markdown code blocks if present)
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]

            legal_brief = json.loads(clean_response.strip())

            # Add metadata
            legal_brief["application_id"] = application_id or "direct_input"
            legal_brief["generated_at"] = datetime.now().isoformat()

            # Save to Supabase if we have an application_id
            if application_id:
                try:
                    supabase.save_legal_brief(application_id, legal_brief)
                    logger.info(f"Saved Legal Brief for application: {application_id}")
                except Exception as e:
                    logger.warning(f"Could not save Legal Brief: {e}")

            # Format output for display
            output = format_legal_brief(legal_brief)

            return TextContent(
                author="agent",
                content=output
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return TextContent(
                author="agent",
                content=f"**Legal Brief Analysis**\n\n{response}"
            )

    except Exception as e:
        logger.error(f"Error generating Legal Brief: {e}", exc_info=True)
        return TextContent(
            author="agent",
            content=f"Error generating Legal Brief: {str(e)}"
        )


def format_legal_brief(brief: dict) -> str:
    """Format the Legal Brief for display."""
    lines = [
        "# Legal Brief",
        f"**Application ID:** {brief.get('application_id', 'N/A')}",
        f"**Generated:** {brief.get('generated_at', 'N/A')}",
        "",
        "---",
        ""
    ]

    # Case Summary
    case_summary = brief.get("case_summary", {})
    if case_summary:
        lines.extend([
            "## Case Summary",
            "",
            f"**Application Number:** {case_summary.get('application_number', 'N/A')}",
            f"**Transaction Type:** {case_summary.get('transaction_type', 'N/A')}",
            f"**Description:** {case_summary.get('transaction_description', 'N/A')}",
            "",
            "---",
            ""
        ])

    # Parties
    parties = brief.get("parties", [])
    if parties:
        lines.extend([
            "## Parties",
            ""
        ])
        for party in parties:
            role = party.get("role", "unknown").upper()
            name_en = party.get("name_en", "N/A")
            name_ar = party.get("name_ar", "N/A")

            lines.append(f"### {role}")
            lines.append(f"- **Name:** {name_en} / {name_ar}")
            lines.append(f"- **QID:** {party.get('qid', 'N/A')}")
            lines.append(f"- **Nationality:** {party.get('nationality', 'N/A')}")

            if party.get("capacity_claimed"):
                lines.append(f"- **Capacity Claimed:** {party.get('capacity_claimed')}")
            if party.get("capacity_evidence"):
                lines.append(f"- **Capacity Evidence:** {party.get('capacity_evidence')}")

            # Additional attributes
            attrs = party.get("additional_attributes", {})
            if attrs:
                for key, value in attrs.items():
                    if value:
                        lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            lines.append("")
    else:
        # Fallback to old grantor/agent structure
        grantor = brief.get("grantor", {})
        if grantor:
            lines.extend([
                "## Parties",
                "",
                "### GRANTOR (First Party)",
                f"- **Name:** {grantor.get('name_en', 'N/A')} / {grantor.get('name_ar', 'N/A')}",
                f"- **QID:** {grantor.get('qid', 'N/A')}",
                f"- **Nationality:** {grantor.get('nationality', 'N/A')}",
                f"- **Capacity:** {grantor.get('capacity_type', 'N/A')}",
                ""
            ])

        agent = brief.get("agent", {})
        if agent:
            lines.extend([
                "### AGENT (Second Party)",
                f"- **Name:** {agent.get('name_en', 'N/A')} / {agent.get('name_ar', 'N/A')}",
                f"- **QID:** {agent.get('qid', 'N/A')}",
                f"- **Nationality:** {agent.get('nationality', 'N/A')}",
                ""
            ])

    # Entity Information
    entity = brief.get("entity_information", {})
    if entity and (entity.get("company_name_en") or entity.get("company_name_ar")):
        lines.extend([
            "---",
            "",
            "## Entity Information",
            "",
            f"**Company Name:** {entity.get('company_name_en', 'N/A')} / {entity.get('company_name_ar', 'N/A')}",
            f"**Registration Number:** {entity.get('registration_number', 'N/A')}",
            f"**Entity Type:** {entity.get('entity_type', 'N/A')}",
            ""
        ])

        authorities = entity.get("registered_authorities", [])
        if authorities:
            lines.append("### Registered Authorities:")
            for auth in authorities:
                if isinstance(auth, dict):
                    name = auth.get("person_name", "N/A")
                    position = auth.get("position", "N/A")
                    scope = auth.get("authority_scope", "N/A")
                    lines.append(f"- **{name}** ({position})")
                    lines.append(f"  - Authority Scope: {scope}")
                else:
                    lines.append(f"- {auth}")
            lines.append("")
    else:
        # Fallback to old company structure
        company = brief.get("company")
        if company:
            lines.extend([
                "---",
                "",
                "## Company",
                "",
                f"- **Name:** {company.get('name_en', 'N/A')} / {company.get('name_ar', 'N/A')}",
                f"- **CR Number:** {company.get('cr_number', 'N/A')}",
                ""
            ])
            managers = company.get("managers", [])
            if managers:
                lines.append("**Managers:**")
                for mgr in managers:
                    if isinstance(mgr, dict):
                        lines.append(f"  - {mgr.get('name', 'N/A')}: {mgr.get('authority', 'N/A')}")
                    else:
                        lines.append(f"  - {mgr}")
                lines.append("")

    # POA Details
    poa = brief.get("poa_details", {})
    if poa:
        lines.extend([
            "---",
            "",
            "## POA Details",
            "",
            f"**POA Type:** {poa.get('poa_type', 'N/A')}",
            f"**Duration:** {poa.get('duration', 'N/A')}",
            f"**Substitution Allowed:** {poa.get('substitution_allowed', 'N/A')}",
            ""
        ])

        powers = poa.get("powers_granted", [])
        if powers:
            lines.append("**Powers Granted:**")
            for p in powers:
                lines.append(f"  - {p}")
            lines.append("")
    else:
        # Fallback to old powers_facts structure
        powers = brief.get("powers_facts", {})
        if powers:
            lines.extend([
                "---",
                "",
                "## Powers Analysis",
                "",
                "**Powers Requested:**"
            ])
            for p in powers.get("powers_requested", []):
                lines.append(f"  - {p}")
            lines.append("")

            if powers.get("powers_out_of_scope"):
                lines.append("**⚠️ Powers OUT OF SCOPE (Beyond Grantor's Authority):**")
                for p in powers.get("powers_out_of_scope", []):
                    lines.append(f"  - ❌ {p}")
                lines.append("")

    # Evidence Summary
    evidence = brief.get("evidence_summary", [])
    if evidence:
        lines.extend([
            "---",
            "",
            "## Evidence Summary",
            ""
        ])
        for e in evidence:
            doc_type = e.get("document_type", "Unknown")
            confidence = e.get("confidence", 0)
            lines.append(f"### {doc_type} (Confidence: {confidence:.0%})")

            facts = e.get("key_facts_extracted", [])
            if facts:
                for fact in facts:
                    lines.append(f"  - {fact}")
            lines.append("")

    # Fact Comparisons (for detecting discrepancies)
    comparisons = brief.get("fact_comparisons", [])
    mismatches = [c for c in comparisons if not c.get("match")]
    if mismatches:
        lines.extend([
            "---",
            "",
            "## ⚠️ Fact Discrepancies Detected",
            ""
        ])
        for c in mismatches:
            fact_type = c.get("fact_type", "unknown")
            source1 = c.get("source_1", {})
            source2 = c.get("source_2", {})
            lines.append(f"### {fact_type.replace('_', ' ').title()}")
            lines.append(f"- **{source1.get('source', 'Source 1')}:** {source1.get('value', 'N/A')}")
            lines.append(f"- **{source2.get('source', 'Source 2')}:** {source2.get('value', 'N/A')}")
            if c.get("notes"):
                lines.append(f"- **Notes:** {c.get('notes')}")
            lines.append("")
    else:
        # Fallback to old discrepancies structure
        discrepancies = brief.get("discrepancies", [])
        if discrepancies:
            lines.extend([
                "---",
                "",
                "## ⚠️ Discrepancies Detected",
                ""
            ])
            for d in discrepancies:
                severity = d.get("severity", "UNKNOWN")
                emoji = "🔴" if severity == "CRITICAL" else "🟡" if severity == "WARNING" else "🔵"
                lines.append(f"{emoji} **{d.get('type', 'UNKNOWN')}** ({severity})")
                lines.append(f"   {d.get('description', 'N/A')}")
                lines.append("")

    # Open Questions for Tier 2
    questions = brief.get("open_questions", [])
    if questions:
        lines.extend([
            "---",
            "",
            "## Open Questions for Tier 2 Legal Research",
            ""
        ])
        for q in questions:
            priority = q.get("priority", "important")
            emoji = "🔴" if priority == "critical" else "🟡" if priority == "important" else "🔵"
            lines.append(f"{emoji} **{q.get('question_id', 'Q')}** [{q.get('category', 'general')}]")
            lines.append(f"   {q.get('question', 'N/A')}")

            relevant_facts = q.get("relevant_facts", [])
            if relevant_facts:
                lines.append("   Relevant facts:")
                for fact in relevant_facts[:3]:  # Limit to first 3
                    lines.append(f"   - {fact}")
            lines.append("")

    # Missing Information
    missing = brief.get("missing_information", [])
    if missing:
        lines.extend([
            "---",
            "",
            "## Missing Information",
            ""
        ])
        for m in missing:
            lines.append(f"- {m}")
        lines.append("")

    # Extraction Confidence
    confidence = brief.get("extraction_confidence", 0)
    lines.extend([
        "---",
        "",
        f"**Extraction Confidence:** {confidence:.0%}",
        ""
    ])

    # JSON output for downstream processing
    lines.extend([
        "---",
        "",
        "<details>",
        "<summary>Raw JSON for Legal Search Agent</summary>",
        "",
        "```json",
        json.dumps(brief, ensure_ascii=False, indent=2),
        "```",
        "</details>"
    ])

    return "\n".join(lines)
