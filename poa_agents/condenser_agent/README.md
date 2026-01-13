# Condenser Agent

The Condenser Agent extracts and organizes facts from POA (Power of Attorney) applications into a structured **Legal Brief** for Tier 2 legal research.

## Overview

This agent is part of the SAK AI validation pipeline. It sits between the raw application data and the Legal Search Agent, transforming unstructured case data into a condensed, research-ready format.

```
Application Data  →  [Condenser Agent]  →  Legal Brief  →  [Legal Search Agent]
```

## Architecture

### Agent Type
- **Framework**: Agentex (FastACP)
- **ACP Type**: Sync (synchronous message handling)
- **Port**: 8012 (local development)

### Components

```
condenser_agent/
├── .env                    # Environment variables (secrets)
├── manifest.yaml           # Agent configuration
├── project/
│   ├── __init__.py
│   ├── acp.py              # Main ACP handler (entry point)
│   ├── llm_client.py       # OpenAI client wrapper
│   └── supabase_client.py  # Database operations
```

## Input/Output

### Input Format

The agent accepts two input formats:

#### 1. By Application ID
```json
{
  "application_id": "a0000001-1111-2222-3333-444444444444"
}
```

The agent will load from Supabase:
- `applications` table - Application metadata
- `parties` table - All parties (grantor, agent, etc.)
- `capacity_proofs` table - Authority evidence for parties
- `document_extractions` table - OCR results from uploaded documents

#### 2. Direct Input
```json
{
  "case_data": {
    "application": {...},
    "parties": [...],
    "capacity_proofs": [...]
  },
  "document_extractions": [...],
  "additional_context": {}
}
```

### Output: Legal Brief

The agent outputs a structured JSON document containing:

```json
{
  "case_summary": {
    "application_number": "SAK-2026-POA-TEST001",
    "transaction_type": "POA_SPECIAL_COMPANY",
    "transaction_description": "Special POA for Company Management"
  },
  "parties": [
    {
      "role": "grantor",
      "name_ar": "حمزة عوض",
      "name_en": "Hamza Awad",
      "qid": "13572468",
      "nationality": "CAN",
      "capacity_claimed": "Manager with signing authority",
      "capacity_evidence": "CR shows: Manager (Passports only)"
    }
  ],
  "entity_information": {
    "company_name_ar": "صولا للخدمات",
    "company_name_en": "Sola Services",
    "registration_number": "3333",
    "registered_authorities": [
      {
        "person_name": "Hamza Awad",
        "position": "Manager",
        "authority_scope": "Passports",
        "id_number": "13572468"
      }
    ]
  },
  "poa_details": {
    "poa_type": "special",
    "powers_granted": [
      "Company Management",
      "Contract Signing",
      "Government Representation"
    ],
    "duration": "indefinite",
    "substitution_allowed": false
  },
  "fact_comparisons": [
    {
      "fact_type": "grantor_authority",
      "source_1": {"source": "POA text", "value": "Full management powers"},
      "source_2": {"source": "CR extract", "value": "Passports only"},
      "match": false,
      "notes": "CRITICAL: Grantor claiming broader authority than CR shows"
    }
  ],
  "open_questions": [
    {
      "question_id": "Q1",
      "category": "capacity",
      "question": "Can a manager with 'Passports only' authority grant full management powers?",
      "relevant_facts": ["CR shows Passports authority", "POA grants full management"],
      "priority": "critical"
    }
  ],
  "extraction_confidence": 0.85
}
```

### UI Display

The agent formats the output for display with:
- Case Summary section
- Parties with roles and capacities
- Entity information with registered authorities
- POA details with granted powers
- Fact discrepancies highlighted with warnings
- Open questions for Tier 2 research
- Raw JSON in collapsible section

## Environment Variables

Create a `.env` file in the agent directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...your-key...
LLM_MODEL=gpt-4o-mini

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...your-anon-key...
```

## Running the Agent

### Local Development

```bash
# Navigate to agent directory
cd poa_agents/condenser_agent

# Start the agent using Agentex CLI
agentex dev
```

The agent will start on `http://localhost:8012`.

### Using the Agentex UI

1. Open the Agentex UI (typically `http://localhost:3000`)
2. Select "condenser-agent" from the agent list
3. Send a message with the application ID:
   ```json
   {"application_id": "a0000001-1111-2222-3333-444444444444"}
   ```
4. The agent will respond with the formatted Legal Brief

### Programmatic Usage

```python
import httpx

async def call_condenser():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8012/acp/send",
            json={
                "content": {
                    "content": '{"application_id": "a0000001-1111-2222-3333-444444444444"}'
                }
            }
        )
        return response.json()
```

## Database Schema

The agent reads from the following Supabase tables:

### `applications`
Main application records with transaction type, status, and duration.

### `parties`
All parties involved with roles (grantor, agent), identity info, and capacity.

### `capacity_proofs`
Evidence of capacity including:
- CR (Commercial Registration) details
- POA text (Arabic/English)
- Granted powers

### `document_extractions`
OCR results from uploaded documents, containing:
- Raw text (Arabic/English)
- Structured extracted fields
- OCR confidence scores

### `legal_briefs`
Output storage:
- `brief_content` (JSONB) - The full Legal Brief
- `completeness_score` - Extraction confidence
- `issues_to_analyze` - Open questions for Tier 2

## LLM Prompting

The agent uses a detailed system prompt that instructs the LLM to:

1. **Extract ALL facts** - Names, dates, numbers, authorities, powers
2. **Quote exact text** - From documents where relevant
3. **Compare sources** - What POA claims vs what CR shows
4. **Generate questions** - For any legal issues needing research
5. **Note missing info** - What's not available but relevant

The temperature is set to `0.2` for consistent, focused extraction.

## Error Handling

- Invalid JSON input is treated as a plain application ID
- Missing application returns helpful error message
- Failed LLM parsing returns raw response
- Database errors are logged and surfaced to user

## Integration with Legal Search Agent

The Legal Brief is:
1. Saved to `legal_briefs` table in Supabase
2. Retrieved by Legal Search Agent via `application_id`
3. Used as input for legal issue decomposition and RAG search

## Development

### File Structure

| File | Purpose |
|------|---------|
| `acp.py` | Main handler, prompt templates, output formatting |
| `llm_client.py` | OpenAI AsyncClient wrapper |
| `supabase_client.py` | Database queries for case data |
| `manifest.yaml` | Agent configuration for Agentex |

### Key Functions

- `handle_message_send()` - Main ACP handler
- `format_legal_brief()` - Formats output for UI display
- `CondenserLLMClient.chat()` - Calls OpenAI API
- `CondenserSupabaseClient.get_*()` - Database queries
