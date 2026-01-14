# Legal Search Agent

The Legal Search Agent performs **statute-grounded legal research** on POA applications using **Agentic RAG** (Retrieval-Augmented Generation) with HyDE to determine validity based on Qatari civil and commercial law.

## Overview

This is the Tier 2 agent in the SAK AI validation pipeline. It takes a Legal Brief from the Condenser Agent and:
1. **Decomposes** the case into specific legal sub-issues
2. **Retrieves** relevant legal articles using **Agentic RAG** (HyDE + iterative refinement)
3. **Synthesizes** a comprehensive legal opinion with citations
4. **Determines** validity: VALID, INVALID, VALID_WITH_CONDITIONS, or NEEDS_REVIEW

```
Legal Brief  →  [Decomposer]  →  [Agentic RAG Loop]  →  [Synthesizer]  →  Legal Opinion
```

## Architecture

### Agent Type
- **Framework**: Agentex (FastACP)
- **ACP Type**: Sync (synchronous message handling)
- **Port**: 8013 (local development)

### Components

```
legal_search_agent/
├── .env                    # Environment variables (secrets)
├── manifest.yaml           # Agent configuration
├── project/
│   ├── __init__.py
│   ├── acp.py              # Main ACP handler (entry point)
│   ├── llm_client.py       # OpenAI client wrapper (chat + embeddings)
│   ├── supabase_client.py  # Database operations + RAG search
│   ├── models/
│   │   ├── __init__.py
│   │   └── retrieval_state.py  # State models for agentic retrieval
│   ├── config/
│   │   └── legal_areas.yaml    # Required legal areas per transaction type
│   └── components/
│       ├── __init__.py
│       ├── decomposer.py       # Breaks case into legal issues
│       ├── retriever.py        # Legacy retriever (replaced)
│       ├── hyde_generator.py   # HyDE hypothetical generation
│       ├── coverage_analyzer.py # Legal area coverage analysis
│       ├── crossref_expander.py # Cross-reference expansion
│       ├── retrieval_agent.py  # Agentic RAG orchestrator
│       └── synthesizer.py      # Generates legal opinion
```

## Agentic RAG Pipeline

### Phase 1: Decomposition

The Decomposer analyzes the Legal Brief and generates legal sub-issues with Arabic search queries:

```json
{
  "issue_id": "ISSUE_1",
  "category": "grantor_capacity",
  "primary_question": "Does the grantor have authority to delegate these powers?",
  "search_queries_ar": [
    "لا يجوز للموكل أن يمنح الوكيل صلاحيات تزيد عما يملكه",
    "حدود الوكالة",
    "أهلية الموكل في الوكالة"
  ],
  "priority": 1
}
```

### Phase 2: Agentic Retrieval (NEW)

The RetrievalAgent orchestrates a multi-iteration retrieval loop:

#### Iteration 1: Broad Retrieval with HyDE

1. **HyDE Generation**: Convert each legal question into hypothetical Arabic legal articles
   ```
   Question: "هل يجوز للموكل تفويض صلاحيات لا يملكها؟"

   HyDE Output:
   "المادة (هـ): لا يجوز للموكل أن يمنح الوكيل حقوقاً أو صلاحيات
    تزيد عما يملكه الموكل نفسه من حقوق قانونية أو أهلية..."
   ```

2. **Semantic Search**: Search with HyDE hypotheticals + direct Arabic queries
3. **Coverage Analysis**: Check which legal areas are covered

#### Iteration 2: Gap-Filling

1. Identify missing required legal areas (e.g., `delegation_limits`, `capacity`)
2. Generate targeted queries for each gap
3. Apply HyDE to gap-filling queries
4. Search and add new articles

#### Iteration 3: Cross-Reference Expansion

1. Parse retrieved articles for cross-references (e.g., "المادة 5")
2. Fetch referenced articles directly from database
3. Enable multi-hop legal reasoning

#### End Conditions

The loop stops when ANY of these conditions is met:

| Condition | Threshold |
|-----------|-----------|
| Coverage score | ≥ 80% of required areas |
| Confidence | ≥ 55% avg similarity + ≥ 65% top-3 |
| Max iterations | 3 iterations |
| Max articles | 30 articles |
| Max latency | 30 seconds |
| Diminishing returns | ≤ 1 new article in iteration |

### Phase 3: Synthesis

The Synthesizer generates a comprehensive legal opinion with citations.

## Required Legal Areas

The agent ensures coverage of these legal areas (from `config/legal_areas.yaml`):

| Area ID | Arabic Name | Required |
|---------|-------------|----------|
| `agency_law` | قانون الوكالة | Yes |
| `delegation_limits` | حدود التفويض | Yes |
| `capacity` | الأهلية القانونية | Yes |
| `commercial_registration` | السجل التجاري | Conditional (if entity) |
| `formalities` | الشكليات | No |
| `poa_scope` | نطاق الوكالة | No |

## Evaluation Artifacts

Every retrieval run saves a detailed artifact to `retrieval_eval_artifacts` table:

```json
{
  "artifact_id": "uuid",
  "iterations": [
    {
      "iteration_number": 1,
      "purpose": "broad_retrieval",
      "queries": [
        {
          "query_text": "حدود الوكالة",
          "hypothetical_generated": "المادة (هـ): ...",
          "articles_found": [90001, 90002],
          "similarities": [0.72, 0.68]
        }
      ],
      "coverage_before": {"agency_law": "missing", ...},
      "coverage_after": {"agency_law": "covered", ...}
    }
  ],
  "stop_reason": "coverage_threshold_met",
  "coverage_score": 0.85,
  "avg_similarity": 0.65
}
```

## Input/Output

### Input Format

#### 1. By Application ID
```json
{
  "application_id": "a0000001-1111-2222-3333-444444444444"
}
```
The agent loads the Legal Brief from the `legal_briefs` table.

#### 2. Direct Legal Brief
```json
{
  "legal_brief": {
    "parties": [...],
    "entity_information": {...},
    "poa_details": {...}
  }
}
```

### Output: Legal Opinion

The agent produces:
1. **Formatted Display** - Markdown with verdict, analysis, citations, retrieval metrics
2. **JSON Storage** - Full opinion saved to `legal_opinions` table
3. **Eval Artifact** - Full retrieval trace saved to `retrieval_eval_artifacts`

#### UI Display Format (with Retrieval Metrics)

```markdown
# ❌ Legal Research Opinion

**Application ID:** a0000001-1111-2222-3333-444444444444
**Generated:** 2026-01-13T12:00:00

---

## Decision

### ❌ Finding: **INVALID**
### Confidence: **85%** (HIGH)

---

## Verification Metrics

- **Grounding Score:** 85%
- **Retrieval Coverage:** 100%

### Agentic Retrieval Details

- **Iterations:** 2
- **Stop Reason:** coverage_threshold_met
- **Articles Retrieved:** 12
- **Coverage Score:** 85%
- **Avg Similarity:** 65%
- **Top-3 Similarity:** 78%
- **LLM Calls (HyDE):** 4
- **Embedding Calls:** 8
- **Latency:** 5230ms
- **Est. Cost:** $0.0052
```

## Environment Variables

Create a `.env` file in the agent directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=YOUR_OPENAI_KEY
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...your-anon-key...

# Search Configuration
SIMILARITY_THRESHOLD=0.3
MAX_ARTICLES_PER_ISSUE=5
```

## Running the Agent

### Local Development

```bash
# Navigate to agent directory
cd poa_agents/legal_search_agent

# Start the agent using Agentex CLI
agentex dev
```

The agent will start on `http://localhost:8013`.

### Database Migrations

Run the retrieval artifacts migration:

```bash
# In Supabase SQL Editor, run:
migrations/003_retrieval_eval_artifacts.sql
```

## Component Details

### HydeGenerator (`components/hyde_generator.py`)

- **Purpose**: Generate hypothetical Arabic legal articles
- **LLM Model**: GPT-4o-mini (temperature: 0.7)
- **Output Format**: Articles starting with "المادة (هـ):"
- **Key Feature**: Bridges query-document semantic gap

### CoverageAnalyzer (`components/coverage_analyzer.py`)

- **Purpose**: Track which legal areas are covered
- **Input**: List of articles + required areas config
- **Output**: Coverage status per area (covered/weak/missing)
- **Gaps**: Identifies missing areas with suggested queries

### CrossRefExpander (`components/crossref_expander.py`)

- **Purpose**: Parse cross-references from Arabic legal text
- **Patterns**: Detects "المادة (5)", "وفقاً للمادة", "انظر المادة", etc.
- **Output**: Fetches referenced articles for multi-hop reasoning

### RetrievalAgent (`components/retrieval_agent.py`)

- **Purpose**: Orchestrate the agentic RAG loop
- **Iterations**: Up to 3 (broad → gap-filling → reference expansion)
- **State**: Tracks articles, coverage, queries tried
- **Artifact**: Saves full trace for evaluation

### Decomposer (`components/decomposer.py`)

- **Purpose**: Break Legal Brief into researchable legal issues
- **LLM Model**: GPT-4o-mini (temperature: 0.2)
- **Output**: List of issues with Arabic search queries

### Synthesizer (`components/synthesizer.py`)

- **Purpose**: Generate comprehensive legal opinion from evidence
- **LLM Model**: GPT-4o-mini (temperature: 0.2, max_tokens: 4000)
- **Citation Requirements**: Every conclusion must cite specific articles

## Verification Metrics

| Metric | Description |
|--------|-------------|
| `grounding_score` | % of findings supported by article citations |
| `retrieval_coverage` | Coverage score from agentic retrieval |
| `confidence_score` | Overall confidence in the verdict |
| `avg_similarity` | Average similarity across all retrieved articles |
| `top_3_similarity` | Average similarity of top 3 articles |

## Decision Buckets

| Bucket | Meaning |
|--------|---------|
| `valid` | POA is legally valid, can proceed |
| `valid_with_remediations` | Valid if conditions are met |
| `invalid` | POA is legally invalid, must reject |
| `needs_review` | Insufficient evidence, requires SME |

## Testing RAG Quality

Check the retrieval metrics in the output:

### Similarity Scores
- **> 70%**: Excellent match (high confidence)
- **50-70%**: Good match (moderate confidence)
- **30-50%**: Fair match (low confidence)
- **< 30%**: Below threshold (not returned)

### Coverage Score
- **> 80%**: All required legal areas covered
- **50-80%**: Partial coverage, may need gap-filling
- **< 50%**: Poor coverage, needs more iterations

### Stop Reasons
- `coverage_threshold_met`: Ideal - found enough evidence
- `confidence_threshold_met`: Good - high quality matches
- `max_iterations_reached`: May need larger corpus
- `diminishing_returns`: Corpus may not have relevant articles
