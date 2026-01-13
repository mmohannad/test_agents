# SAK AI Agent - Agentex Implementation Plan

> **Based on:** ML Committee Report (Jan 2, 2026)  
> **Framework:** Agentex (Temporal Workflows) + Deterministic Python Services  
> **Status:** Planning

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [What's an Agent vs What's Not](#whats-an-agent-vs-whats-not)
3. [Agent Specifications](#agent-specifications)
4. [Deterministic Services](#deterministic-services)
5. [Data Flow](#data-flow)
6. [Supabase Schema Requirements](#supabase-schema-requirements)
7. [Implementation Phases](#implementation-phases)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SAK AI VALIDATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    DETERMINISTIC (Python Services)                        │   │
│  │                                                                           │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                │   │
│  │  │   Supabase   │    │    Data      │    │    Case      │                │   │
│  │  │   (Source)   │───▶│  Extraction  │───▶│   Builder    │                │   │
│  │  └──────────────┘    │   (Python)   │    │   (Python)   │                │   │
│  │                      └──────────────┘    └──────────────┘                │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         AGENTEX AGENT (LLM-Powered)                       │   │
│  │                                                                           │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │   │
│  │  │                       VISION AGENT                                │    │   │
│  │  │   ┌─────────┐   ┌─────────────┐   ┌─────────────┐                │    │   │
│  │  │   │   OCR   │──▶│  Classify   │──▶│  Extract    │                │    │   │
│  │  │   │  (VLM)  │   │    Doc      │   │   Fields    │                │    │   │
│  │  │   └─────────┘   └─────────────┘   └─────────────┘                │    │   │
│  │  └──────────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│                            ┌──────────────────────┐                              │
│                            │   VIRTUAL CASE       │                              │
│                            │      OBJECT          │                              │
│                            └──────────────────────┘                              │
│                                        │                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    DETERMINISTIC (Python Functions)                       │   │
│  │                                                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐     │   │
│  │  │                    TIER 1: VALIDATION CHECKS                     │     │   │
│  │  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │     │   │
│  │  │  │  Requirements   │ │ Reconciliation  │ │    Validity     │    │     │   │
│  │  │  │    Checker      │ │    Checker      │ │    Checker      │    │     │   │
│  │  │  └─────────────────┘ └─────────────────┘ └─────────────────┘    │     │   │
│  │  └─────────────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                          ┌─────────────┴─────────────┐                          │
│                          ▼                           ▼                          │
│                    [TIER 1 PASS]              [TIER 1 FAIL]                     │
│                          │                           │                          │
│  ┌───────────────────────┴───────────────────────────┴───────────────────────┐  │
│  │                         AGENTEX AGENTS (LLM-Powered)                       │  │
│  │                                                                            │  │
│  │  ┌──────────────────┐                      ┌──────────────────┐           │  │
│  │  │    CONDENSER     │                      │   Risk Scoring   │           │  │
│  │  │      AGENT       │                      │   (Deterministic)│           │  │
│  │  │   (LLM Brief)    │                      └────────┬─────────┘           │  │
│  │  └────────┬─────────┘                               │                     │  │
│  │           │                                         ▼                     │  │
│  │           ▼                               [INVALID + REMEDIATION]         │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │  │
│  │  │                   LEGAL SEARCH AGENT (TIER 2)                     │    │  │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────┐ │    │  │
│  │  │  │Decomposer │▶│ Retriever │▶│ Packager  │▶│Synthesizer│▶│Verify│ │    │  │
│  │  │  │   (LLM)   │ │   (RAG)   │ │   (LLM)   │ │   (LLM)   │ │(LLM)│ │    │  │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └─────┘ │    │  │
│  │  └──────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         DETERMINISTIC (Python)                            │   │
│  │                                                                           │   │
│  │                     ┌──────────────────────┐                              │   │
│  │                     │   RISK SCORING &     │                              │   │
│  │                     │      ROUTING         │                              │   │
│  │                     └──────────────────────┘                              │   │
│  │                              │                                            │   │
│  │          ┌───────────────────┼───────────────────┐                       │   │
│  │          ▼                   ▼                   ▼                       │   │
│  │     [VALID]          [CONDITIONAL]          [ESCALATE]                   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Design Philosophy

1. **Deterministic code = Python services** (data extraction, tier 1 checks, risk scoring)
2. **LLM-powered = Agentex agents** (vision, condenser, legal search)
3. **Clear separation** - Agents only where AI/LLM reasoning is required

---

## What's an Agent vs What's Not

### ✅ AGENTEX AGENTS (3 total)

These require LLM/VLM capabilities:

| Agent | Why It Needs LLM |
|-------|------------------|
| **Vision Agent** | VLM for OCR, document classification, field extraction from images |
| **Condenser Agent** | LLM to summarize case facts into a tight Legal Brief |
| **Legal Search Agent** | LLM for decomposition, RAG retrieval, synthesis, verification |

### ❌ NOT AGENTS (Deterministic Python)

These are pure rule-based logic - direct DB access, no LLM needed:

| Service | Why It's Deterministic |
|---------|------------------------|
| **Data Extraction** | SQL queries, template parsing, field normalization |
| **Case Builder** | Data transformation, merging SQL + evidence |
| **Tier 1 Validation** | Rule-based checks (requirements, reconciliation, validity) |
| **Risk Scoring** | Formula-based composite scores, threshold comparisons |

---

## Agent Specifications

### Agent 1: Vision Agent

**Purpose:** Process attachments (PDFs/images) → structured evidence using VLM.

**Type:** `Agentic` (Temporal) - handles multiple attachments, needs LLM/VLM

**Port:** 8011  
**Queue:** `vision_queue`

```
┌─────────────────────────────────────────────────────┐
│                   VISION AGENT                       │
├─────────────────────────────────────────────────────┤
│ INPUT:                                               │
│   - application_id: str                              │
│   - attachment_ids: str[] (optional, else all)       │
│                                                      │
│ ACTIVITIES (per attachment):                         │
│   1. ocr_extract        → raw text + bounding boxes  │
│   2. classify_document  → document_type_code + conf  │
│   3. extract_fields     → entities (QID, names, etc) │
│   4. map_to_schema      → canonical evidence format  │
│                                                      │
│ OUTPUT:                                              │
│   - extractions: DocumentExtraction[]                │
│   - poa_extraction: POAExtraction (if POA doc)       │
│   - classification_results: DocClassification[]      │
│   - extraction_confidence: float                     │
└─────────────────────────────────────────────────────┘
```

**Why it's an agent:** Requires VLM/LLM for:
- OCR with layout understanding
- Document type classification (QID vs POA vs Trade License)
- Intelligent field extraction from noisy/varied documents

**Key Tables Updated:**
- `attachments` - file metadata, ocr_status
- `document_extractions` - raw OCR + extracted fields
- `poa_extractions` - POA-specific structured data

**manifest.yaml:**
```yaml
agent:
  name: vision-agent
  acp_type: agentic
  description: OCR, document classification, and field extraction
  temporal:
    enabled: true
    workflows:
      - name: vision-workflow
        queue_name: vision_queue

local_development:
  agent:
    port: 8011
  paths:
    acp: project/acp.py
    worker: project/run_worker.py

  env:
    AZURE_OPENAI_ENDPOINT: "..."
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: "..."
    LLM_MODEL: "gpt-4o"
```

---

### Agent 2: Condenser Agent

**Purpose:** Create a tight "Legal Brief" for Tier 2 reasoning using LLM summarization.

**Type:** `Sync` (single LLM call, no complex workflow)

**Port:** 8012

```
┌─────────────────────────────────────────────────────┐
│                 CONDENSER AGENT                      │
├─────────────────────────────────────────────────────┤
│ INPUT:                                               │
│   - virtual_case_object: VirtualCaseObject           │
│   - fact_sheet: FactSheet (from Tier 1)              │
│                                                      │
│ PROCESSING (LLM):                                    │
│   1. Filter facts relevant to legal capacity/        │
│      authority/scope/substitution                    │
│   2. Compose structured brief with provenance        │
│   3. Identify open questions for Tier 2              │
│                                                      │
│ OUTPUT (Legal Brief):                                │
│   - parties_summary: str                             │
│   - roles_summary: str                               │
│   - poa_facts: POAFactsSummary                       │
│   - tier1_summary: str                               │
│   - open_questions: str[]                            │
│   - uncertainties: Uncertainty[]                     │
└─────────────────────────────────────────────────────┘
```

**Why it's an agent:** Requires LLM to:
- Intelligently filter and prioritize facts
- Compose coherent legal brief in structured format
- Identify what questions Tier 2 needs to answer

**Legal Brief Contents:**
- Parties, roles, core identifiers
- Relevant POA facts (powers, substitution, dates)
- Tier 1 results summary (pass + warnings)
- Open questions/uncertainties to resolve in Tier 2

**manifest.yaml:**
```yaml
agent:
  name: condenser-agent
  acp_type: sync
  description: Creates Legal Brief for Tier 2 research

local_development:
  agent:
    port: 8012
  paths:
    acp: project/acp.py

  env:
    LLM_MODEL: "gpt-4o"
```

---

### Agent 3: Legal Search Agent (Tier 2)

**Purpose:** Statute-grounded legal reasoning with decomposition, RAG, and verification.

**Type:** `Agentic` (Temporal) - complex multi-phase workflow with multiple LLM calls

**Port:** 8013  
**Queue:** `legal_search_queue`

**Submodules (all LLM-powered):**
1. **Decomposer** - Break into legal sub-issues
2. **Iterative Retriever** - RAG with multiple queries
3. **Evidence Packager** - Build citation ledger
4. **Synthesizer** - Produce legal opinion
5. **Grounding & Stability Tester** - Verify trustworthiness

```
┌─────────────────────────────────────────────────────┐
│              LEGAL SEARCH AGENT (TIER 2)             │
├─────────────────────────────────────────────────────┤
│ INPUT:                                               │
│   - legal_brief: LegalBrief                          │
│   - transaction_type: str                            │
│                                                      │
│ WORKFLOW PHASES:                                     │
│                                                      │
│ Phase 1: DECOMPOSE (LLM)                             │
│   - Break "Is this POA valid?" into sub-issues:      │
│     • Grantor capacity                               │
│     • Agent authority                                │
│     • Scope of powers                                │
│     • Substitution rights                            │
│     • Formalities                                    │
│                                                      │
│ Phase 2: ITERATIVE RETRIEVE (RAG + LLM)              │
│   - Per issue: query articles vector store           │
│   - LLM generates search queries                     │
│   - Multiple iterations, refinements                 │
│   - Output: per-issue evidence sets                  │
│                                                      │
│ Phase 3: PACKAGE EVIDENCE (LLM)                      │
│   - Build citation ledger                            │
│   - Every claim → article span                       │
│                                                      │
│ Phase 4: SYNTHESIZE (LLM)                            │
│   - Produce legal opinion                            │
│   - Candidate decision bucket                        │
│   - Conditions/remediations if applicable            │
│                                                      │
│ Phase 5: VERIFY (LLM)                                │
│   - Grounding score: claims with citations           │
│   - Retrieval success: per-issue coverage            │
│   - Stability: bucket consistency across runs        │
│   - Flag contradictions, weak evidence               │
│                                                      │
│ OUTPUT:                                              │
│   - decision_bucket: VALID | INVALID | CONDITIONAL   │
│   - legal_opinion: str                               │
│   - citations: Citation[]                            │
│   - conditions: str[] (if applicable)                │
│   - grounding_score: float                           │
│   - stability_score: float                           │
│   - retrieval_coverage: dict                         │
│   - flags: Flag[]                                    │
└─────────────────────────────────────────────────────┘
```

**Why it's an agent:** This is the core agentic reasoning:
- LLM decomposes complex legal questions
- RAG retrieves relevant statutes
- LLM synthesizes findings into legal opinion
- LLM verifies its own reasoning

**Knowledge Sources:**
- `articles` table - legal text + embeddings
- Vector similarity search for RAG

**manifest.yaml:**
```yaml
agent:
  name: legal-search-agent
  acp_type: agentic
  description: Deep legal research with RAG (Tier 2)
  temporal:
    enabled: true
    workflows:
      - name: legal-search-workflow
        queue_name: legal_search_queue

local_development:
  agent:
    port: 8013
  paths:
    acp: project/acp.py
    worker: project/run_worker.py

  env:
    LLM_MODEL: "gpt-4o"
    EMBEDDING_MODEL: "text-embedding-3-small"
    MAX_RETRIEVAL_ITERATIONS: "3"
    STABILITY_RUNS: "2"
```

---

## Deterministic Services

These are **NOT agents** - they're Python modules/functions called directly.

### Service 1: Data Extraction

**Purpose:** Convert SQL record into structured data representation.

**Location:** `shared/data_extraction.py`

```python
# Functions (not an agent)
def extract_application(application_id: str) -> dict:
    """Load application from Supabase."""
    
def parse_template(application: dict) -> TemplateObject:
    """Parse template selections + free text."""
    
def build_parties_and_roles(application: dict) -> tuple[list[Party], list[Role]]:
    """Build parties[] and roles[] from SQL fields."""
    
def normalize_to_schema(parsed_data: dict) -> dict:
    """Normalize to canonical schema."""
```

---

### Service 2: Case Builder

**Purpose:** Assemble Virtual Case Object from SQL + Vision evidence.

**Location:** `shared/case_builder.py`

```python
def build_case_object(
    application_id: str,
    sql_data: dict,
    evidence_extractions: dict
) -> VirtualCaseObject:
    """
    Merge SQL-derived parties with evidence.
    Add provenance + confidence per field.
    Flag uncertainties/conflicts.
    """
```

---

### Service 3: Tier 1 Validation

**Purpose:** Deterministic validation checks (requirements, reconciliation, validity).

**Location:** `shared/tier1_validation.py` (or keep existing `tier1_validation_agent/project/checks/`)

```python
def check_requirements(case: VirtualCaseObject, config: TransactionConfig) -> list[Check]:
    """Check required parties/docs exist."""
    
def check_reconciliation(case: VirtualCaseObject) -> list[Check]:
    """Cross-check identifiers across sources."""
    
def check_validity(case: VirtualCaseObject) -> list[Check]:
    """Validate dates, expiry, chronological consistency."""
    
def run_all_tier1_checks(case: VirtualCaseObject, config: TransactionConfig) -> FactSheet:
    """Run all checks and return fact sheet."""
```

**Check Examples:**
```python
# Requirements Checker
- principal present
- POA document required  
- QIDs required for each party role
- If principal is entity → board resolution required

# Reconciliation Checker
- QID on uploaded ID matches party record
- principal/agent identity consistency across documents
- POA document names/QIDs align with declared parties

# Validity Checker
- QID not expired
- Trade license not expired
- POA expiry later than issue date
- POA not older than validity window
```

---

### Service 4: Risk Scoring

**Purpose:** Deterministic composite scoring and routing.

**Location:** `shared/risk_scoring.py`

```python
def calculate_composite_score(
    fact_sheet: FactSheet,
    legal_opinion: Optional[LegalOpinion],
    verification_metrics: Optional[VerificationMetrics]
) -> float:
    """
    Combine signals:
    - extraction_completeness
    - tier1_gate_result
    - grounding_score
    - stability_score
    - retrieval_success
    """

def apply_routing_policy(composite_score: float, flags: list[str]) -> str:
    """
    Policy thresholds:
    - AUTO_APPROVE: >= 0.85
    - MANUAL_REVIEW: 0.6 - 0.85
    - ESCALATE: < 0.6
    """
    
def score_and_route(
    fact_sheet: FactSheet,
    legal_opinion: Optional[LegalOpinion] = None
) -> RiskScore:
    """Main entry point for risk scoring."""
```

---

## Data Flow

```
┌────────────────┐
│  Application   │
│   Submitted    │
└───────┬────────┘
        │
        ▼
┌────────────────┐     ┌────────────────┐
│ applications   │────▶│ Data Extraction│  ◀── Python function
│ (SQL table)    │     │   (Python)     │      (NOT an agent)
└────────────────┘     └───────┬────────┘
                               │
┌────────────────┐             │ sql_case_structure
│  attachments   │─────┐       │
│ (file storage) │     │       │
└────────────────┘     │       │
        │              ▼       │
        │      ┌───────────────┴───┐
        └─────▶│   VISION AGENT    │  ◀── AGENTEX AGENT #1
               │      (VLM)        │      (LLM-powered)
               └───────────────┬───┘
                               │ evidence_extractions
                               │
                               ▼
                    ┌──────────────────┐
                    │ Case Builder     │  ◀── Python function
                    │    (Python)      │      (NOT an agent)
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ VIRTUAL CASE     │
                    │    OBJECT        │◀──── Central Artifact
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Tier 1 Validation│  ◀── Python function
                    │    (Python)      │      (NOT an agent)
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               [PASS]            [FAIL]
                    │                 │
                    ▼                 ▼
           ┌───────────────┐  ┌───────────────┐
           │   CONDENSER   │  │ Risk Scoring  │  ◀── Python function
           │     AGENT     │  │   (Python)    │
           └───────┬───────┘  └───────┬───────┘
                   │  ▲               │
                   │  │               ▼
    AGENTEX AGENT #2  │         [INVALID +
       (LLM-powered)  │         REMEDIATION]
                   │
                   ▼
           ┌───────────────┐
           │ LEGAL BRIEF   │
           └───────┬───────┘
                   │
                   ▼
           ┌───────────────┐
           │ LEGAL SEARCH  │  ◀── AGENTEX AGENT #3
           │    AGENT      │      (LLM + RAG)
           └───────┬───────┘
                   │
                   ▼
           ┌───────────────┐
           │ Risk Scoring  │  ◀── Python function
           │   (Python)    │      (NOT an agent)
           └───────┬───────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    [VALID]  [CONDITIONAL] [ESCALATE]
```

### Summary

| Component | Type | Reason |
|-----------|------|--------|
| Data Extraction | Python | Direct DB queries, deterministic |
| **Vision Agent** | **AGENT** | **Needs VLM for OCR/classification** |
| Case Builder | Python | Pure data transformation |
| Tier 1 Validation | Python | Rule-based checks |
| **Condenser Agent** | **AGENT** | **Needs LLM for summarization** |
| **Legal Search Agent** | **AGENT** | **Needs LLM + RAG for research** |
| Risk Scoring | Python | Formula-based scoring |

---

## Supabase Schema Requirements

> **✅ Migration Already Applied:** The comprehensive schema (`supabase_data_model_arch.md`) has been run.
> 27 tables + 24 enums created. No additional DDL needed.

### Reference Tables (6)
| Table | Purpose | Seeded |
|-------|---------|--------|
| `transaction_types` | POA/Sale transaction definitions | ✅ 10 rows |
| `transaction_configs` | Per-type validation rules | |
| `capacity_configurations` | Party capacity definitions | ✅ 14 rows |
| `attachment_types` | Document type definitions | ✅ 12 rows |
| `template_definitions` | POA template text | |
| `articles` | Legal corpus for RAG | Populate separately |

### Core Tables (8)
| Table | Purpose |
|-------|---------|
| `applications` | Main application records |
| `parties` | Parties (party_type + party_role) |
| `capacity_proofs` | Proof of capacity (merged from old poa_extractions) |
| `capacity_principals` | Principals linked to capacity proofs |
| `documents` | Uploaded documents (renamed from attachments) |
| `document_extractions` | OCR and field extraction results |
| `poa_templates` | Selected templates per application |
| `duplicate_checks` | Party duplicate detection |

### ML Pipeline Tables (15)
| Table | Purpose | Used By |
|-------|---------|---------|
| `document_classifications` | ML document type classification | Vision Agent |
| `extracted_fields` | Normalized extracted fields | Vision Agent |
| `case_objects` | Virtual Case Object (unified JSON) | Case Builder |
| `validation_reports` | Tier 1 validation results | Tier 1 Validation |
| `fact_sheets` | Tier 1 output with blockers/open questions | Tier 1 Validation |
| `legal_briefs` | Condenser output for Tier 2 | Condenser Agent |
| `legal_analysis_sessions` | Tier 2 processing sessions | Legal Search Agent |
| `issue_decompositions` | Sub-questions from Decomposer | Legal Search Agent |
| `retrieved_evidence` | RAG results from articles | Legal Search Agent |
| `research_traces` | Tier 2 audit trail | Legal Search Agent |
| `legal_opinions` | Final Tier 2 opinions | Legal Search Agent |
| `citations` | Links claims → articles | Legal Search Agent |
| `risk_scores` | Composite risk calculation | Risk Scoring |
| `routing_decisions` | Final routing decision | Risk Scoring |
| `escalations` | Cases requiring human review | Pipeline |

### Key Enums
```
application_status, processing_stage, party_type, party_role, capacity_type,
party_capacity, principal_type, ocr_status, case_build_status, brief_status,
analysis_status, issue_category, research_status, risk_level, decision_bucket,
routing_decision_type, routing_target, ...
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Update Supabase schema with new tables
- [ ] Create `shared/data_extraction.py` (Python service)
- [ ] Create `shared/case_builder.py` (Python service)
- [ ] Refactor `shared/tier1_validation.py` from existing agent code
- [ ] Create `shared/risk_scoring.py` (Python service)
- [ ] Test deterministic pipeline: SQL → Case Object → Tier 1 → Risk Score

### Phase 2: Vision Agent (Week 2-3)
- [ ] Create `vision_agent/` with Temporal workflow
- [ ] Implement OCR activity (Azure Document Intelligence or VLM)
- [ ] Implement document classifier activity
- [ ] Implement field extraction activity
- [ ] Test: attachments → extractions → merge with Case Object

### Phase 3: Legal Research Agents (Week 3-4)
- [ ] Create `condenser_agent/` (Sync agent)
- [ ] Create `legal_search_agent/` with all 5 phases
- [ ] Implement RAG with articles vector store
- [ ] Implement stability testing
- [ ] Test Tier 2 pipeline

### Phase 4: Integration & Pipeline (Week 4-5)
- [ ] Create pipeline runner script (not an agent, just orchestration code)
- [ ] End-to-end integration testing
- [ ] Policy threshold tuning
- [ ] Performance benchmarking

### Phase 5: Production Hardening (Week 5-6)
- [ ] Error handling and retries
- [ ] Observability and tracing
- [ ] Prompt optimization
- [ ] Load testing

---

## Directory Structure

```
poa_agents/
├── shared/                          # Shared utilities + deterministic services
│   ├── __init__.py
│   ├── llm_client.py               # Azure OpenAI client
│   ├── supabase_client.py          # Supabase data access
│   ├── rag_client.py               # RAG for legal articles
│   ├── schema.py                   # Shared Pydantic models
│   │
│   ├── data_extraction.py          # ◀── Deterministic service
│   ├── case_builder.py             # ◀── Deterministic service  
│   ├── tier1_validation.py         # ◀── Deterministic service
│   └── risk_scoring.py             # ◀── Deterministic service
│
├── vision_agent/                    # ◀── AGENTEX AGENT #1
│   ├── manifest.yaml
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── project/
│       ├── __init__.py
│       ├── acp.py
│       ├── workflow.py
│       ├── run_worker.py
│       ├── schema.py
│       └── activities/
│           ├── __init__.py
│           ├── ocr.py
│           ├── classifier.py
│           └── extractor.py
│
├── condenser_agent/                 # ◀── AGENTEX AGENT #2
│   ├── manifest.yaml
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── project/
│       ├── __init__.py
│       ├── acp.py
│       ├── schema.py
│       └── prompts/
│           └── condense_brief.jinja2
│
├── legal_search_agent/              # ◀── AGENTEX AGENT #3
│   ├── manifest.yaml
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── project/
│       ├── __init__.py
│       ├── acp.py
│       ├── workflow.py
│       ├── run_worker.py
│       ├── schema.py
│       ├── custom_activities.py
│       ├── components/
│       │   ├── __init__.py
│       │   ├── decomposer.py
│       │   ├── retriever.py
│       │   ├── packager.py
│       │   ├── synthesizer.py
│       │   └── verifier.py
│       └── prompts/
│           ├── decompose.jinja2
│           ├── synthesize.jinja2
│           └── verify.jinja2
│
├── pipeline/                        # Pipeline orchestration (NOT an agent)
│   ├── __init__.py
│   ├── runner.py                   # Main pipeline runner
│   └── config.py                   # Pipeline configuration
│
├── README.md
├── agents_plan.md
└── SCHEMA.md
```

---

## Open Questions for Review

1. **Vision Agent Parallelism:** Process all attachments in parallel or sequential?
2. **Stability Testing:** How many runs for stability check? (Currently set to 2)
3. **Policy Thresholds:** Confirm AUTO_APPROVE (0.85), MANUAL_REVIEW (0.6-0.85), ESCALATE (<0.6)
4. **Condenser Prompt:** Should Legal Brief be in Arabic, English, or both?
5. **Pipeline Orchestration:** Python script, Temporal workflow, or triggered by Supabase events?

---

## Summary

### 3 Agentex Agents (LLM-powered)

| Agent | Port | Type | Purpose |
|-------|------|------|---------|
| `vision-agent` | 8011 | Agentic (Temporal) | OCR, classify, extract from attachments |
| `condenser-agent` | 8012 | Sync | Create Legal Brief for Tier 2 |
| `legal-search-agent` | 8013 | Agentic (Temporal) | Tier 2 deep research with RAG |

### 4 Deterministic Services (Python)

| Service | Location | Purpose |
|---------|----------|---------|
| Data Extraction | `shared/data_extraction.py` | Parse SQL → structured data |
| Case Builder | `shared/case_builder.py` | Merge SQL + evidence → Case Object |
| Tier 1 Validation | `shared/tier1_validation.py` | Requirements, reconciliation, validity checks |
| Risk Scoring | `shared/risk_scoring.py` | Composite scoring → routing decision |

---

## Next Steps

1. **Review this plan** - Confirm agent vs service boundaries
2. **Start Phase 1** - Build deterministic services in `shared/`
3. **Build Vision Agent** - OCR + classification + extraction
4. **Build Legal Agents** - Condenser + Legal Search
5. **Integrate** - Connect everything with pipeline runner

---

*Document Version: 1.1*  
*Last Updated: Jan 12, 2026*

