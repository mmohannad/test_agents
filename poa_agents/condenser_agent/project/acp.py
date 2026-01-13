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


SYSTEM_PROMPT = """You are a legal analyst responsible for extracting and organizing facts from POA (Power of Attorney) and other notarization applications.

Your task is to:
1. Extract ALL relevant facts from the provided data
2. Identify ALL parties and their roles, capacities, and attributes
3. Extract ALL powers/authorities being requested or granted
4. Identify ANY evidence that establishes or limits a party's capacity
5. Note ANY discrepancies between claimed facts and evidenced facts
6. Generate legal questions that need research based on the facts

IMPORTANT PRINCIPLES:
- Be THOROUGH - extract every fact that could be legally relevant
- Be OBJECTIVE - report facts as found, do not make legal conclusions
- Be PRECISE - quote exact text from documents where possible
- COMPARE sources - note where different documents say different things
- IDENTIFY GAPS - note what information is missing

You are preparing a comprehensive fact package for a legal research agent that will determine validity.
The legal agent needs COMPLETE information to make accurate determinations."""


ANALYSIS_PROMPT_TEMPLATE = """Extract and organize ALL facts from the following application data into a comprehensive Legal Brief.

## APPLICATION DATA:
{case_data}

## DOCUMENT EXTRACTIONS:
{document_extractions}

## ADDITIONAL CONTEXT:
{additional_context}

---

Create a comprehensive Legal Brief by extracting ALL facts. Use this structure:

{{
    "case_summary": {{
        "application_number": "...",
        "transaction_type": "...",
        "transaction_description": "..."
    }},
    "parties": [
        {{
            "role": "grantor|agent|seller|buyer|etc",
            "name_ar": "...",
            "name_en": "...",
            "qid": "...",
            "nationality": "...",
            "capacity_claimed": "What capacity they claim to act in",
            "capacity_evidence": "What documents/records show about their capacity",
            "additional_attributes": {{}}
        }}
    ],
    "entity_information": {{
        "company_name_ar": "...",
        "company_name_en": "...",
        "registration_number": "...",
        "entity_type": "...",
        "registered_authorities": [
            {{
                "person_name": "...",
                "position": "...",
                "authority_scope": "exact text from CR",
                "id_number": "..."
            }}
        ]
    }},
    "poa_details": {{
        "poa_type": "general|special",
        "poa_text_ar": "full text if available",
        "poa_text_en": "full text if available",
        "powers_granted": ["list each power separately"],
        "duration": "...",
        "substitution_allowed": true|false|unknown
    }},
    "evidence_summary": [
        {{
            "document_type": "...",
            "key_facts_extracted": ["..."],
            "confidence": 0.0-1.0
        }}
    ],
    "fact_comparisons": [
        {{
            "fact_type": "e.g., grantor_authority",
            "source_1": {{"source": "POA text", "value": "..."}},
            "source_2": {{"source": "CR extract", "value": "..."}},
            "match": true|false,
            "notes": "..."
        }}
    ],
    "open_questions": [
        {{
            "question_id": "Q1",
            "category": "capacity|authority|scope|formalities|validity|compliance",
            "question": "Specific legal question that needs research",
            "relevant_facts": ["facts that prompted this question"],
            "priority": "critical|important|supplementary"
        }}
    ],
    "missing_information": ["List any information that would be relevant but is not available"],
    "extraction_confidence": 0.0-1.0
}}

INSTRUCTIONS:
1. Extract EVERY fact - names, dates, numbers, authorities, powers
2. Quote exact text from documents where relevant
3. Compare what different sources say about the same fact
4. Generate questions for any legal issues that need research
5. Note any missing information that would be relevant

Return ONLY the JSON object."""


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

        else:
            # Direct input
            case_data = input_data.get("case_data", {})
            document_extractions = input_data.get("document_extractions", [])
            additional_context = input_data.get("additional_context", {})

        if not case_data:
            return TextContent(
                author="agent",
                content="No case data available. Please provide application_id or case_data."
            )

        # Build the analysis prompt
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            case_data=json.dumps(case_data, ensure_ascii=False, indent=2, default=str),
            document_extractions=json.dumps(document_extractions, ensure_ascii=False, indent=2, default=str) if document_extractions else "No document extractions available",
            additional_context=json.dumps(additional_context, ensure_ascii=False, indent=2, default=str) if additional_context else "None"
        )

        logger.info("Generating Legal Brief with LLM...")

        # Call LLM to generate the brief
        response = await llm.chat(
            user_message=prompt,
            system_message=SYSTEM_PROMPT
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
