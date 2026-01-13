# SAK POA Validation System - Implementation Plan
## Using AgentEx Multi-Agent Architecture

---

## Overview

This document outlines the implementation plan for the POA (Power of Attorney) validation system using the **two-tier architecture** described in `SAK_ASSISTANT_ARCHITECTURE.md`. The system will be built as a collection of **AgentEx agents** following the established patterns from the council_of_ministers project.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Multiple AgentEx agents** | Separation of concerns, independent scaling, tracing built-in |
| **Temporal workflows** | Long-running tasks, durability, child workflow orchestration |
| **No custom trace tables** | AgentEx provides tracing out-of-box |
| **Existing schema sufficient** | Schema already supports two-tier model |
| **RAG via existing `articles` table** | Legal corpus already in Supabase with embeddings |

---

## Agent Architecture

### Directory Structure

Following the council_of_ministers pattern, agents will be organized in a sibling directory structure:

```
/Users/musa.mohannad/dev/work/test_agents/
├── search_agent/                    # Current - keep as utility agent
│   ├── manifest.yaml
│   ├── project/
│   │   ├── acp.py
│   │   ├── llm_client.py
│   │   └── search_client.py         # RAG functionality
│   └── ...
│
├── poa_agents/                       # NEW - parent directory
│   ├── extraction_agent/             # Document OCR + structured extraction
│   │   ├── manifest.yaml
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── project/
│   │       ├── acp.py
│   │       ├── workflow.py
│   │       ├── run_worker.py
│   │       ├── custom_activities.py
│   │       └── schema.py
│   │
│   ├── tier1_validation_agent/       # Deterministic validation
│   │   ├── manifest.yaml
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── project/
│   │       ├── acp.py
│   │       ├── workflow.py
│   │       ├── run_worker.py
│   │       ├── custom_activities.py
│   │       ├── checks/               # Tier 1 check implementations
│   │       │   ├── field_completeness.py
│   │       │   ├── format_validation.py
│   │       │   ├── cross_field_logic.py
│   │       │   ├── document_matching.py
│   │       │   └── business_rules.py
│   │       └── schema.py
│   │
│   ├── legal_research_agent/         # Tier 2 deep research (main brain)
│   │   ├── manifest.yaml
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── project/
│   │       ├── acp.py
│   │       ├── workflow.py           # Orchestrator + research loop
│   │       ├── run_worker.py
│   │       ├── custom_activities.py
│   │       ├── custom_workflows.py   # SubQuestionWorkflow
│   │       ├── components/
│   │       │   ├── decomposer.py     # Question decomposition
│   │       │   ├── researcher.py     # RAG + analysis
│   │       │   ├── synthesizer.py    # Combine findings
│   │       │   └── verifier.py       # Reflection pass
│   │       ├── prompts/
│   │       │   ├── decomposition.jinja
│   │       │   ├── research.jinja
│   │       │   ├── synthesis.jinja
│   │       │   └── verification.jinja
│   │       └── schema.py
│   │
│   ├── orchestrator_agent/           # Coordinates all agents
│   │   ├── manifest.yaml
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── project/
│   │       ├── acp.py
│   │       ├── workflow.py           # Main workflow
│   │       ├── run_worker.py
│   │       ├── custom_activities.py
│   │       └── schema.py
│   │
│   └── shared/                       # Shared utilities
│       ├── __init__.py
│       ├── llm_client.py
│       ├── supabase_client.py
│       ├── rag_client.py             # Wraps search_agent or direct Supabase
│       └── schema.py                 # Shared Pydantic models
```

---

## Agent Specifications

### 1. Extraction Agent

**Purpose:** Process uploaded documents via OCR/VLM and extract structured data.

```yaml
# manifest.yaml
agent:
  acp_type: agentic
  name: poa-extraction-agent
  description: Extracts structured data from POA documents and supporting documents
  temporal:
    enabled: true
    workflows:
      - name: poa-extraction-workflow
        queue_name: poa_extraction_queue
```

**Input:**
```python
class ExtractionInput(BaseModel):
    application_id: str
    attachment_ids: list[str]
```

**Output:**
```python
class ExtractionOutput(BaseModel):
    document_extractions: list[DocumentExtraction]
    poa_extraction: Optional[POAExtraction]
    extraction_confidence: float
```

**Workflow:**
1. Fetch attachments from Supabase storage
2. Run OCR (Azure Document Intelligence)
3. Run VLM for structured extraction
4. Save to `document_extractions` and `poa_extractions` tables
5. Return structured data

---

### 2. Tier 1 Validation Agent

**Purpose:** Run deterministic checks on application data. Fast, rule-based validation.

```yaml
# manifest.yaml
agent:
  acp_type: agentic
  name: poa-tier1-validation-agent
  description: Performs deterministic validation checks on POA applications
  temporal:
    enabled: true
    workflows:
      - name: poa-tier1-validation-workflow
        queue_name: poa_tier1_validation_queue
```

**Input:**
```python
class Tier1ValidationInput(BaseModel):
    application_id: str
    transaction_type_code: str
```

**Output:**
```python
class Tier1ValidationOutput(BaseModel):
    overall_status: Literal["PASS", "FAIL", "WARNINGS"]
    checks: list[CheckResult]
    blocking_failures: int
    warnings: int
    can_proceed_to_tier2: bool
```

**Checks Implemented (in code, not database):**
```python
# project/checks/field_completeness.py
CHECKS = {
    "field_completeness": check_field_completeness,
    "format_validation": check_format_validation,
    "cross_field_logic": check_cross_field_logic,
    "referential_integrity": check_referential_integrity,
    "document_matching": check_document_matching,
    "business_rules": check_business_rules,
}
```

**Workflow:**
1. Load application + parties + attachments from Supabase
2. Load `transaction_config` for this transaction type
3. Run each Tier 1 check function
4. Aggregate results
5. Save to `validation_reports` table with `tier='tier1'`
6. Return result with `can_proceed_to_tier2`

---

### 3. Legal Research Agent (Tier 2)

**Purpose:** Deep legal reasoning with question decomposition, RAG, and verification.

```yaml
# manifest.yaml
agent:
  acp_type: agentic
  name: poa-legal-research-agent
  description: Performs deep legal research for POA validity assessment
  temporal:
    enabled: true
    workflows:
      - name: poa-legal-research-workflow
        queue_name: poa_legal_research_queue
```

**Input:**
```python
class LegalResearchInput(BaseModel):
    application_id: str
    case_bundle: CaseBundle  # Assembled by orchestrator
    tier1_report_id: str
```

**Output:**
```python
class LegalOpinionOutput(BaseModel):
    finding: Literal["VALID", "INVALID", "VALID_WITH_CONDITIONS", "REQUIRES_REVIEW", "INCONCLUSIVE"]
    confidence: float  # 0.0 - 1.0
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    analysis: dict  # Per sub-question
    concerns: list[str]
    recommendations: list[str]
    legal_citations: list[Citation]
    opinion_text: str  # Markdown
```

**Workflow (implements deep research pattern):**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      LEGAL RESEARCH WORKFLOW                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. DECOMPOSITION PHASE                                                   │
│     ├─ Activity: decompose_question                                       │
│     │   Input: case_bundle, transaction_type                              │
│     │   Output: sub_questions[] with priorities                           │
│     │                                                                     │
│  2. RESEARCH PHASE (parallel child workflows)                             │
│     ├─ For each sub_question (parallel):                                  │
│     │   └─ Child Workflow: SubQuestionResearchWorkflow                    │
│     │       ├─ Activity: retrieve_legal_context (RAG)                     │
│     │       │   → Query articles table via semantic search                │
│     │       ├─ Activity: analyze_against_facts                            │
│     │       │   → LLM reasoning with retrieved articles                   │
│     │       ├─ Activity: form_preliminary_finding                         │
│     │       └─ If follow_up_needed:                                       │
│     │           └─ Recursive: deeper research (max_depth=3)               │
│     │                                                                     │
│  3. SYNTHESIS PHASE                                                       │
│     ├─ Activity: synthesize_findings                                      │
│     │   Input: all sub_question findings                                  │
│     │   Output: draft_opinion                                             │
│     │                                                                     │
│  4. VERIFICATION PHASE                                                    │
│     ├─ Activity: verify_opinion                                           │
│     │   Input: draft_opinion                                              │
│     │   Output: verified_opinion, issues_found                            │
│     │                                                                     │
│  5. FINALIZATION                                                          │
│     ├─ Save to legal_opinions table                                       │
│     ├─ Update validation_reports.legal_opinion_id                         │
│     └─ If confidence < 0.6: trigger escalation                            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

**Child Workflow for Sub-Questions:**

```python
@workflow.defn(name="sub-question-research")
class SubQuestionResearchWorkflow:
    
    @workflow.run
    async def run(self, params: SubQuestionParams) -> SubQuestionFinding:
        # Step 1: Retrieve legal context
        articles = await workflow.execute_activity(
            RETRIEVE_LEGAL_CONTEXT,
            RetrieveLegalContextParams(
                query=params.sub_question.question,
                legal_areas=params.sub_question.legal_areas,
            ),
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Step 2: Analyze
        analysis = await workflow.execute_activity(
            ANALYZE_LEGAL_CONTEXT,
            AnalyzeLegalContextParams(
                sub_question=params.sub_question,
                retrieved_articles=articles,
                case_facts=params.case_facts,
            ),
            start_to_close_timeout=timedelta(minutes=10),
        )
        
        # Step 3: Check if follow-up needed
        if analysis.follow_up_needed and params.current_depth < MAX_DEPTH:
            follow_up_finding = await workflow.execute_child_workflow(
                SubQuestionResearchWorkflow.run,
                SubQuestionParams(
                    sub_question=SubQuestion(
                        question=analysis.follow_up_question,
                        ...
                    ),
                    current_depth=params.current_depth + 1,
                ),
            )
            analysis.incorporate_follow_up(follow_up_finding)
        
        return SubQuestionFinding(
            sub_question_id=params.sub_question.id,
            finding=analysis.finding,
            confidence=analysis.confidence,
            legal_basis=analysis.legal_basis,
            analysis_text=analysis.analysis_text,
        )
```

---

### 4. Orchestrator Agent

**Purpose:** Coordinates the full validation pipeline.

```yaml
# manifest.yaml
agent:
  acp_type: agentic
  name: poa-orchestrator-agent
  description: Orchestrates the full POA validation pipeline
  temporal:
    enabled: true
    workflows:
      - name: poa-orchestration-workflow
        queue_name: poa_orchestration_queue
```

**Input:**
```python
class OrchestrationInput(BaseModel):
    application_id: str
    run_extraction: bool = True
    run_tier1: bool = True
    run_tier2: bool = True  # Only if tier1 passes
```

**Workflow:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION WORKFLOW                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. LOAD APPLICATION                                                      │
│     └─ Activity: load_application_data                                    │
│                                                                           │
│  2. EXTRACTION (if needed)                                                │
│     └─ Child Workflow → Extraction Agent                                  │
│        agentex_client.create_task("poa-extraction-agent", ...)            │
│                                                                           │
│  3. TIER 1 VALIDATION                                                     │
│     └─ Child Workflow → Tier 1 Agent                                      │
│        agentex_client.create_task("poa-tier1-validation-agent", ...)      │
│                                                                           │
│  4. DECISION GATE                                                         │
│     ├─ IF tier1.blocking_failures > 0:                                    │
│     │   └─ Return early with tier1 results                                │
│     └─ ELSE:                                                              │
│         └─ Continue to Tier 2                                             │
│                                                                           │
│  5. ASSEMBLE CASE BUNDLE                                                  │
│     └─ Activity: assemble_case_bundle                                     │
│        Combines: application + extractions + tier1_results                │
│                                                                           │
│  6. TIER 2 LEGAL RESEARCH                                                 │
│     └─ Child Workflow → Legal Research Agent                              │
│        agentex_client.create_task("poa-legal-research-agent", ...)        │
│                                                                           │
│  7. ESCALATION CHECK                                                      │
│     └─ IF opinion.confidence < 0.6:                                       │
│         └─ Activity: create_escalation                                    │
│                                                                           │
│  8. UPDATE APPLICATION STATUS                                             │
│     └─ Activity: update_application_status                                │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Status

### Already Implemented ✅

The following tables are already in Supabase and support the two-tier architecture:

| Table | Purpose | Status |
|-------|---------|--------|
| `articles` | Legal corpus for RAG | ✅ Ready (has embeddings) |
| `transaction_types` | Transaction categorization | ✅ Seeded with 10 types |
| `transaction_configs` | Per-type structural requirements | ✅ Seeded with 10 configs |
| `role_types` | Party role definitions | ✅ Seeded with 14 roles |
| `capacity_types` | Capacity categorization | ✅ Seeded with 6 types |
| `applications` | Application metadata | ✅ Ready |
| `personal_parties` | Party information | ✅ Ready |
| `application_party_roles` | Party-application links | ✅ Ready |
| `attachments` | Uploaded documents | ✅ Ready |
| `document_types` | Document categorization | ✅ Seeded with 10 types |
| `document_extractions` | OCR results | ✅ Ready |
| `poa_extractions` | POA-specific extractions | ✅ Ready |
| `validation_reports` | Tier 1 results | ✅ Has tier1 fields |
| `research_traces` | Tier 2 audit trail | ✅ Has all needed fields |
| `legal_opinions` | Tier 2 output | ✅ Complete |
| `escalations` | Human review cases | ✅ Updated for both tiers |

### Deprecated (Don't Use) ⚠️

| Table | Status |
|-------|--------|
| `rule_packs` | ⚠️ Marked deprecated |
| `validation_rules` | ⚠️ Marked deprecated |

These tables have `deprecated=true` flag. Tier 1 validation logic is now implemented in code, not database rules.

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal:** Set up agent structure and basic infrastructure.

**Tasks:**
- [ ] Create `poa_agents/` directory structure
- [ ] Set up `shared/` utilities (LLM client, Supabase client, RAG client)
- [ ] Create `extraction_agent/` skeleton with manifest and basic workflow
- [ ] Create `tier1_validation_agent/` skeleton
- [ ] Test agent-to-agent communication pattern

**Deliverables:**
- Working agent directory structure
- Agents can be run locally with `agentex agents run`
- Basic smoke tests

### Phase 2: Extraction Agent (Week 2)

**Goal:** Complete document extraction pipeline.

**Tasks:**
- [ ] Implement OCR activity (Azure Document Intelligence)
- [ ] Implement structured extraction activity
- [ ] Implement POA-specific extraction
- [ ] Save results to Supabase
- [ ] Add extraction confidence scoring

**Deliverables:**
- Extraction agent processes documents end-to-end
- Results saved to `document_extractions` and `poa_extractions`
- Unit tests for extraction logic

### Phase 3: Tier 1 Validation Agent (Week 3)

**Goal:** Complete deterministic validation.

**Tasks:**
- [ ] Implement check functions:
  - [ ] `field_completeness.py`
  - [ ] `format_validation.py`
  - [ ] `cross_field_logic.py`
  - [ ] `referential_integrity.py`
  - [ ] `document_matching.py`
  - [ ] `business_rules.py`
- [ ] Load and use `transaction_configs` from Supabase
- [ ] Generate structured Tier 1 report
- [ ] Save to `validation_reports`

**Deliverables:**
- Tier 1 agent runs all checks
- Clear pass/fail/warning output
- `can_proceed_to_tier2` correctly determined

### Phase 4: Legal Research Agent (Weeks 4-5)

**Goal:** Implement deep research with question decomposition.

**Tasks:**
- [ ] Implement `decomposer.py` - question breakdown
- [ ] Implement `researcher.py` - RAG + analysis
- [ ] Implement `synthesizer.py` - combine findings
- [ ] Implement `verifier.py` - reflection pass
- [ ] Create prompt templates (jinja)
- [ ] Implement `SubQuestionResearchWorkflow` child workflow
- [ ] Handle follow-up questions with depth limits
- [ ] Save to `research_traces` and `legal_opinions`

**Deliverables:**
- Legal research agent produces grounded opinions
- Citations from `articles` table
- Confidence scoring
- Research traces for audit

### Phase 5: Orchestrator + Integration (Week 6)

**Goal:** Full pipeline integration.

**Tasks:**
- [ ] Implement orchestrator workflow
- [ ] Agent-to-agent communication via AgentEx client
- [ ] Escalation logic
- [ ] Application status updates
- [ ] Error handling and retries

**Deliverables:**
- End-to-end pipeline: intake → extraction → tier1 → tier2 → output
- Escalation flow working
- All agents communicating correctly

### Phase 6: Testing & Evaluation (Week 7)

**Goal:** Validate system accuracy.

**Tasks:**
- [ ] Create test applications with known outcomes
- [ ] Run evaluation suite
- [ ] Compare agent opinions to SME judgments
- [ ] Tune prompts and confidence thresholds
- [ ] Document failure modes

**Deliverables:**
- Accuracy metrics documented
- Prompt optimizations applied
- Known limitations documented

---

## AgentEx Patterns to Follow

### 1. Agent Communication

From `workflow_service.py` in council_of_ministers backend:

```python
from agentex.types.agent_rpc_params import (
    ParamsCreateTaskRequest,
    ParamsSendEventRequest,
)
from agentex.types.data_content_param import DataContentParam

# Create task on another agent
task = await agentex_client.agents.create_task(
    agent_name="poa-legal-research-agent",
    params=ParamsCreateTaskRequest(
        name=f"{workflow_id}",
        params={
            "input": case_bundle,
            "tier1_report_id": tier1_report.id,
        },
    ),
)

# Send start event
await agentex_client.agents.send_event(
    agent_name="poa-legal-research-agent",
    params=ParamsSendEventRequest(
        content=DataContentParam(
            author="orchestrator",
            type="data",
            data={"message": "start_task"},
        ),
        task_id=str(task.result.id),
    ),
)
```

### 2. Workflow Structure

From `benchmarking_agent/project/workflow.py`:

```python
@workflow.defn(name=environment_variables.WORKFLOW_NAME)
class POAValidationWorkflow(BaseWorkflow):
    
    def __init__(self):
        super().__init__(display_name=environment_variables.AGENT_NAME)
        self._start_task = False
    
    @workflow.signal(name=SignalName.RECEIVE_EVENT)
    async def on_task_event_send(self, params: SendEventParams) -> None:
        if (
            params.event.content is not None
            and params.event.content.type == "data"
            and params.event.content.data.get("message") == "start_task"
        ):
            self._start_task = True
    
    @workflow.run
    async def on_task_create(self, params: CreateTaskParams) -> str:
        # Wait for start signal
        await workflow.wait_condition(lambda: self._start_task)
        
        # Execute activities...
```

### 3. Custom Activities

From `benchmarking_agent/project/custom_activities.py`:

```python
class CustomActivities:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.supabase = get_supabase_client()
    
    @activity.defn(name=UPDATE_WORKFLOW_STATUS)
    async def update_workflow_status(self, params: UpdateWorkflowStatusActivityParams) -> None:
        # Implementation...
```

### 4. Tracing (Built-in)

AgentEx provides automatic tracing. We store correlation IDs in our tables:

```sql
-- Already in schema
agent_name VARCHAR,          -- Name of the AgentEx agent
agentex_trace_id VARCHAR     -- Correlation ID from AgentEx tracing
```

Access traces via AgentEx dashboard or API - no need to build custom trace capture.

---

## RAG Implementation

### Using Existing Search Client

The `search_agent/project/search_client.py` already implements semantic search:

```python
async def semantic_search(
    self,
    query_embedding: list[float],
    match_count: int = 5,
    similarity_threshold: float = 0.3
) -> list[dict]:
    """
    Uses the match_articles Supabase function for vector similarity.
    """
    result = self.client.rpc(
        'match_articles',
        {
            'query_embedding': query_embedding,
            'match_threshold': similarity_threshold,
            'match_count': match_count
        }
    ).execute()
    return result.data
```

### RAG Client for Agents

Create a shared RAG client in `poa_agents/shared/rag_client.py`:

```python
class RAGClient:
    def __init__(self, llm_client: LLMClient, supabase: Client):
        self.llm = llm_client
        self.supabase = supabase
    
    async def retrieve_relevant_articles(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: int = 5,
    ) -> list[Article]:
        # 1. Generate embedding for query
        embedding = await self.llm.get_embedding(query)
        
        # 2. Semantic search via Supabase
        results = self.supabase.rpc(
            'match_articles',
            {
                'query_embedding': embedding,
                'match_threshold': 0.3,
                'match_count': limit,
            }
        ).execute()
        
        # 3. Return structured articles
        return [Article(**r) for r in results.data]
```

---

## Test Data Strategy

### Dummy Applications

Create test applications covering key scenarios:

| Scenario | Transaction Type | Expected Outcome |
|----------|-----------------|------------------|
| Simple valid POA | `general_poa` | VALID |
| Missing grantor ID | `special_litigation_poa` | FAIL (Tier 1) |
| Agent not licensed | `special_litigation_poa` | INVALID (Tier 2) |
| Company POA no resolution | `company_general_poa` | REQUIRES_REVIEW |
| Property sale valid | `special_property_sale_poa` | VALID |
| Expired POA | `general_poa` | FAIL (Tier 1) |
| Cross-border elements | `special_litigation_poa` | REQUIRES_REVIEW |

### Data Generation Script

```python
# scripts/generate_test_data.py
async def generate_test_applications():
    """Generate test applications with all related entities."""
    
    scenarios = [
        SimpleValidPOA(),
        MissingGrantorID(),
        UnlicensedAgent(),
        CompanyNoResolution(),
        # ...
    ]
    
    for scenario in scenarios:
        app = await create_application(scenario.transaction_type)
        parties = await create_parties(app.id, scenario.parties)
        attachments = await create_attachments(app.id, scenario.documents)
        
        if scenario.include_extraction:
            await create_mock_extraction(attachments)
        
        print(f"Created test case: {scenario.name} - {app.id}")
```

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Tier 1 Accuracy | > 99% | Automated tests |
| Tier 2 Agreement with SME | > 80% | SME review of samples |
| False Negative Rate | < 5% | Valid POAs marked invalid |
| False Positive Rate | < 10% | Invalid POAs marked valid |
| Processing Time | < 60s | End-to-end for typical case |
| Escalation Rate | 10-20% | Cases sent to human review |

---

## Next Steps

1. **Create directory structure** for `poa_agents/`
2. **Copy and adapt** agent boilerplate from council_of_ministers
3. **Implement shared utilities** (LLM, Supabase, RAG clients)
4. **Start with Tier 1** - simplest to test
5. **Build up to Tier 2** - most complex component
6. **Integrate via orchestrator**
7. **Generate test data** and evaluate

---

## Appendix: Manifest Templates

### Extraction Agent Manifest

```yaml
build:
  context:
    root: ../
    include_paths:
      - extraction_agent
      - shared
    dockerfile: extraction_agent/Dockerfile

local_development:
  agent:
    port: 8010
    host_address: host.docker.internal
  paths:
    acp: project/acp.py
    worker: project/run_worker.py

agent:
  acp_type: agentic
  name: poa-extraction-agent
  description: Extracts structured data from POA documents
  temporal:
    enabled: true
    workflows:
      - name: poa-extraction-workflow
        queue_name: poa_extraction_queue
  env:
    AZURE_OPENAI_ENDPOINT: "https://..."
    AZURE_OPENAI_API_VERSION: "2025-01-01-preview"
    LLM_MODEL: "gpt-4o"
    SUPABASE_URL: "https://..."
```

### Legal Research Agent Manifest

```yaml
build:
  context:
    root: ../
    include_paths:
      - legal_research_agent
      - shared
    dockerfile: legal_research_agent/Dockerfile

local_development:
  agent:
    port: 8012
    host_address: host.docker.internal
  paths:
    acp: project/acp.py
    worker: project/run_worker.py

agent:
  acp_type: agentic
  name: poa-legal-research-agent
  description: Performs deep legal research for POA validity assessment
  temporal:
    enabled: true
    workflows:
      - name: poa-legal-research-workflow
        queue_name: poa_legal_research_queue
  env:
    AZURE_OPENAI_ENDPOINT: "https://..."
    AZURE_OPENAI_API_VERSION: "2025-01-01-preview"
    LLM_MODEL: "gpt-4o"
    EMBEDDING_MODEL: "text-embedding-3-small"
    SUPABASE_URL: "https://..."
```
