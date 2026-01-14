# SAK AI Agent - POA Validation System

Multi-agent system for Power of Attorney (POA) validation using AgentEx Temporal workflows.

> **Status:** Architecture redesign in progress. See `agents_plan.md` for the new design based on the ML Committee Report.

---

## Quick Start (Tier 1 Agent - Legacy)

```bash
# 1. Navigate to the agent
cd poa_agents/tier1_validation_agent

# 2. Create virtual environment and install dependencies
uv venv && source .venv/bin/activate && uv sync

# 3. Create .env file (see Environment Setup below)

# 4. Run the agent (starts both ACP server + Temporal worker)
source .venv/bin/activate
export $(cat .env | xargs)
agentex agents run --manifest manifest.yaml

# 5. Test via curl (in another terminal)
curl -X POST http://localhost:5003/agents/name/poa-tier1-validation-agent/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "task/create",
    "params": {
      "name": "test-validation",
      "params": {"sak_case_number": "SAK-2024-POA-00001"}
    },
    "id": 1
  }'
```

---

## Architecture

```
poa_agents/
├── shared/                          # Shared utilities
│   ├── llm_client.py               # Azure OpenAI client
│   ├── supabase_client.py          # Supabase data access
│   ├── rag_client.py               # RAG for legal articles
│   └── schema.py                   # Shared Pydantic models
│
├── tier1_validation_agent/          # Deterministic validation
│   ├── manifest.yaml               # Agent configuration
│   ├── .env                        # Environment variables (create this)
│   ├── project/
│   │   ├── acp.py                  # ACP server entry point
│   │   ├── workflow.py             # Tier 1 Temporal workflow
│   │   ├── run_worker.py           # Temporal worker runner
│   │   ├── custom_activities.py    # Tier 1 activities
│   │   └── checks/                 # Validation check implementations
│   │       ├── field_completeness.py
│   │       ├── format_validation.py
│   │       ├── cross_field_logic.py
│   │       ├── document_matching.py
│   │       └── business_rules.py
│
├── legal_research_agent/            # Deep legal research (Tier 2)
│   ├── manifest.yaml
│   ├── project/
│   │   ├── workflow.py             # Research workflow
│   │   ├── custom_activities.py    # Research activities
│   │   └── components/             # Research components
│   │       ├── decomposer.py       # Question decomposition
│   │       ├── researcher.py       # RAG + analysis
│   │       ├── synthesizer.py      # Finding synthesis
│   │       └── verifier.py         # Opinion verification
│
└── orchestrator_agent/              # Pipeline orchestration
    ├── manifest.yaml
    └── project/
        ├── workflow.py             # Orchestration workflow
        └── custom_activities.py    # Coordination activities
```

---

## Tier 1 Validation Agent (Detailed)

### What It Does

The Tier 1 agent performs **fast, deterministic validation checks** on POA applications. It runs 5 validation checks and determines if an application can proceed to Tier 2 (legal research).

### Input Arguments

The agent accepts input in the task `params` as JSON:

**Option 1: By SAK Case Number (recommended)**
```json
{
  "sak_case_number": "SAK-2024-POA-00001"
}
```

**Option 2: By Application UUID**
```json
{
  "application_id": "a1000001-0001-0001-0001-000000000001"
}
```

### The 5 Validation Checks

| Check | What It Validates | Severity |
|-------|-------------------|----------|
| **Field Completeness** | Required fields present (QID, names, parties, documents) | BLOCKING |
| **Format Validation** | QID format (11 digits), date validity, phone/email patterns, POA expiry | BLOCKING |
| **Cross-Field Logic** | Party uniqueness, date ranges valid, role consistency | BLOCKING |
| **Document Matching** | Party names/QIDs match between application data and POA document | NON-BLOCKING |
| **Business Rules** | Transaction-specific rules (value limits, party counts, POA age) | BLOCKING |

### Output & Results Storage

**Results are stored in Supabase `validation_reports` table:**

| Column | Description |
|--------|-------------|
| `id` | Report UUID |
| `application_id` | Link to application |
| `tier` | Always "tier1" |
| `verdict` | PASS / FAIL / WARNINGS |
| `rules_passed` | Count of passed checks |
| `rules_failed` | Count of failed checks |
| `blocking_failures` | Count of blocking failures |
| `can_proceed_to_tier2` | Boolean - if true, can run Tier 2 |
| `checks_run` | JSON array with detailed check results |
| `processing_time_ms` | Execution time |
| `agent_name` | "poa-tier1-validation-agent" |

**Query results:**
```sql
SELECT * FROM validation_reports 
WHERE application_id = 'your-uuid' 
ORDER BY created_at DESC LIMIT 1;
```

---

## Environment Setup

### Prerequisites

1. **AgentEx Backend** running (provides Temporal server at `localhost:7233`)
   ```bash
   cd /path/to/scale-agentex/agentex
   make dev
   ```

2. **Python 3.12+** and **uv** package manager

3. **Supabase** project with POA schema

### Create `.env` File

Create `tier1_validation_agent/.env`:

```bash
# Supabase (REQUIRED)
SUPABASE_URL=https://cjidkejfazctyqhkfmzz.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Temporal (REQUIRED - provided by AgentEx backend)
TEMPORAL_ADDRESS=localhost:7233

# Workflow Configuration (REQUIRED)
WORKFLOW_NAME=poa-tier1-validation-workflow
WORKFLOW_TASK_QUEUE=poa_tier1_validation_queue
AGENT_NAME=poa-tier1-validation-agent

# Environment
ENVIRONMENT=development
```

### Install & Run

```bash
cd tier1_validation_agent

# Setup
uv venv && source .venv/bin/activate && uv sync

# Load env vars and run
export $(cat .env | xargs)
agentex agents run --manifest manifest.yaml
```

This starts:
- **ACP Server** on `http://localhost:8010`
- **Temporal Worker** connected to `poa_tier1_validation_queue`

---

## API Usage

### Create Validation Task (curl)

```bash
curl -X POST http://localhost:5003/agents/name/poa-tier1-validation-agent/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "task/create",
    "params": {
      "name": "validate-case-001",
      "params": {
        "sak_case_number": "SAK-2024-POA-00001"
      }
    },
    "id": 1
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "1ac40bc8-f7d2-451c-af9c-c617da9cedf8",
    "name": "validate-case-001",
    "status": "RUNNING",
    "params": {"sak_case_number": "SAK-2024-POA-00001"}
  }
}
```

### Check Task Status

```bash
curl http://localhost:5003/tasks/{task_id}
```

### Python SDK

```python
from agentex import AgentexClient

client = AgentexClient()

# Create task
response = await client.agents.rpc(
    agent_name="poa-tier1-validation-agent",
    method="task/create",
    params={
        "name": "validate-my-case",
        "params": {"sak_case_number": "SAK-2024-POA-00001"}
    }
)

task_id = response.result.id
print(f"Task created: {task_id}")
```

### AgentEx UI

1. Open `http://localhost:3000`
2. Find `poa-tier1-validation-agent` in agent list
3. Click "Create Task"
4. Enter JSON: `{"sak_case_number": "SAK-2024-POA-00001"}`
5. Watch results stream in

---

## New Architecture (In Progress)

See **`agents_plan.md`** for the complete redesigned architecture based on the ML Committee Report.

### Design Philosophy

- **Deterministic code = Python services** (data extraction, tier 1 checks, risk scoring)
- **LLM-powered = Agentex agents** (vision, condenser, legal search)

### 3 Agentex Agents (LLM-powered)

| Agent | Port | Type | Purpose |
|-------|------|------|---------|
| `vision-agent` | 8011 | Agentic | OCR, document classification, field extraction (VLM) |
| `condenser-agent` | 8012 | Sync | Create Legal Brief for Tier 2 (LLM) |
| `legal-search-agent` | 8013 | Agentic | Deep research with RAG (Tier 2) |

### 4 Deterministic Services (Python - NOT agents)

| Service | Location | Purpose |
|---------|----------|---------|
| Data Extraction | `shared/data_extraction.py` | Parse SQL → structured data |
| Case Builder | `shared/case_builder.py` | Merge SQL + evidence → Case Object |
| Tier 1 Validation | `shared/tier1_validation.py` | Requirements, reconciliation, validity checks |
| Risk Scoring | `shared/risk_scoring.py` | Composite scoring → routing decision |

### Key Concepts

1. **Virtual Case Object** - Central artifact combining SQL + evidence data
2. **Fact Sheet** - Structured Tier 1 results with evidence pointers
3. **Legal Brief** - Condensed facts for Tier 2 reasoning
4. **Risk Scoring** - Deterministic routing based on measured artifacts (not LLM confidence)

---

## Test Data

The system has 11 test POA applications in Supabase:

| # | Case | Expected Outcome |
|---|------|-----------------|
| 1 | SAK-2024-POA-00001 | ✅ VALID |
| 2 | SAK-2024-POA-00002 | ✅ VALID |
| 3 | SAK-2024-POA-00003 | ❌ TIER 1 FAIL (missing QID) |
| 4 | SAK-2024-POA-00004 | ✅ VALID |
| 5 | SAK-2024-POA-00005 | ⚠️ REQUIRES_REVIEW |
| 6 | SAK-2024-POA-00006 | ⚠️ REQUIRES_REVIEW |
| 7 | SAK-2024-POA-00007 | ❌ TIER 1 FAIL (expired QID) |
| 8 | SAK-2024-POA-00008 | ✅ VALID |
| 9 | SAK-2024-POA-00009 | ❌ TIER 2 FAIL (sub-delegation prohibited) |
| 10 | SAK-2024-POA-00010 | ❌ TIER 2 FAIL (unlicensed attorney) |
| 11 | SAK-2024-POA-00011 | ❌ TIER 2 FAIL (minor grantor) |

## Configuration

### All Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anonymous/publishable key |
| `TEMPORAL_ADDRESS` | ✅ | Temporal server address (default: localhost:7233) |
| `WORKFLOW_NAME` | ✅ | Workflow name (e.g., poa-tier1-validation-workflow) |
| `WORKFLOW_TASK_QUEUE` | ✅ | Temporal task queue name |
| `AGENT_NAME` | ✅ | Agent display name |
| `AZURE_OPENAI_ENDPOINT` | Tier 2 | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Tier 2 | Azure OpenAI API key |
| `LLM_MODEL` | Tier 2 | Chat model deployment name |
| `EMBEDDING_MODEL` | Tier 2 | Embedding model deployment name |
| `MAX_RESEARCH_DEPTH` | Tier 2 | Max follow-up depth for legal research |

---

## Confidence & Escalation (Tier 2)

| Level | Confidence | Action |
|-------|------------|--------|
| HIGH | ≥ 0.8 | Auto-approve/reject |
| MEDIUM | 0.6 - 0.8 | Manual review before approval |
| LOW | < 0.6 | Escalate to SME |

---

## Troubleshooting

### Agent won't start
```bash
# Check if Temporal is running
curl http://localhost:7233

# Check if AgentEx backend is running  
curl http://localhost:5003/agents
```

### "SUPABASE_ANON_KEY is required" error
Make sure `.env` file exists and is loaded:
```bash
cat .env  # Verify file exists
export $(cat .env | xargs)  # Load variables
```

### Task created but no validation runs
Check Temporal worker logs - the worker must be running to process workflows:
```bash
# Look for "Starting workers for task queue" in terminal output
```

### Validation fails with "Application not found"
Verify the case number exists in Supabase:
```sql
SELECT id, sak_case_number FROM applications WHERE sak_case_number = 'SAK-2024-POA-00001';
```

---

## Development

### Adding New Tier 1 Checks

1. Create check function in `tier1_validation_agent/project/checks/new_check.py`:
   ```python
   from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity
   
   def check_new_validation(application: dict, config: dict) -> Tier1CheckResult:
       # Your validation logic
       return Tier1CheckResult(
           category=Tier1CheckCategory.BUSINESS_RULES,
           status=CheckStatus.PASS,
           severity=Severity.NON_BLOCKING,
           message="Check passed"
       )
   ```

2. Import in `custom_activities.py` and add to `check_functions` dict

3. Add check name to `transaction_configs.tier1_checks` in Supabase

### Modifying Research Prompts (Tier 2)

Edit Jinja templates in `legal_research_agent/project/prompts/` or component files in `components/`.

### Adding New Transaction Types

1. Add to `transaction_types` table in Supabase
2. Create `transaction_config` entry with required parties/documents
3. Add type-specific business rules if needed

---

## License

Internal use only.

