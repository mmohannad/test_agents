# SAK AI Agents - POA Validation System

A multi-agent system for validating Power of Attorney (POA) applications using AI-powered legal research. Built on the [Agentex Framework](https://github.com/anthropics/agentex) with RAG (Retrieval-Augmented Generation) for statute-grounded legal analysis.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SAK AI Validation Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐    │
│  │  Application │ ──> │ Condenser Agent  │ ──> │  Legal Search Agent  │    │
│  │    (JSON)    │     │   (Tier 1.5)     │     │      (Tier 2)        │    │
│  └──────────────┘     └──────────────────┘     └──────────────────────┘    │
│        │                      │                         │                    │
│        │                      ▼                         ▼                    │
│        │               ┌─────────────┐          ┌─────────────────┐         │
│        │               │ Legal Brief │          │  Legal Opinion  │         │
│        │               │   (JSON)    │          │ VALID / INVALID │         │
│        │               └─────────────┘          └─────────────────┘         │
│        │                                               │                     │
│        │                      ┌────────────────────────┘                     │
│        │                      ▼                                              │
│        │    ┌─────────────────────────────────────┐                         │
│        └──> │          Supabase Database           │ <── Legal Corpus       │
│             │  (Applications, Parties, Articles)   │     (Arabic + English) │
│             └─────────────────────────────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agents

### 1. Condenser Agent (Tier 1.5)
**Purpose**: Extract and organize facts from POA applications into a structured Legal Brief.

**Capabilities**:
- Loads application data from Supabase (parties, documents, OCR extractions)
- Extracts all relevant facts using LLM analysis
- Compares sources (POA text vs Commercial Registry)
- Identifies discrepancies and generates research questions
- Outputs structured Legal Brief for Tier 2

**Location**: [`poa_agents/condenser_agent/`](./poa_agents/condenser_agent/)

### 2. Legal Search Agent (Tier 2)
**Purpose**: Perform statute-grounded legal research and determine POA validity.

**Capabilities**:
- Decomposes Legal Brief into specific legal sub-issues
- Performs RAG search over Arabic legal corpus
- Retrieves relevant articles using semantic embeddings
- Synthesizes comprehensive legal opinion with citations
- Determines verdict: VALID, INVALID, VALID_WITH_CONDITIONS, or NEEDS_REVIEW

**Location**: [`poa_agents/legal_search_agent/`](./poa_agents/legal_search_agent/)

## Quick Start

### Prerequisites

- Python 3.12+
- Agentex CLI installed
- Supabase project with database schema
- OpenAI API key

### 1. Database Setup

Run the migrations in your Supabase SQL Editor:

```bash
# 1. Create the full schema (27 tables + 24 enums)
migrations/001_new_data_model.sql

# 2. Seed test case data (Hamza Awad test case)
migrations/002_seed_test_case.sql

# 3. Generate embeddings for test articles
python migrations/003_generate_embeddings.py
```

### 2. Environment Setup

Create `.env` files for each agent:

**`poa_agents/condenser_agent/.env`**:
```env
OPENAI_API_KEY=sk-proj-...your-key...
LLM_MODEL=gpt-4o-mini
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...your-anon-key...
```

**`poa_agents/legal_search_agent/.env`**:
```env
OPENAI_API_KEY=sk-proj-...your-key...
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...your-anon-key...
SIMILARITY_THRESHOLD=0.3
MAX_ARTICLES_PER_ISSUE=5
```

### 3. Run the Agents

```bash
# Terminal 1: Start Condenser Agent
cd poa_agents/condenser_agent
agentex dev  # Starts on port 8012

# Terminal 2: Start Legal Search Agent
cd poa_agents/legal_search_agent
agentex dev  # Starts on port 8013
```

### 4. Test with Sample Case

Using the Agentex UI:

1. **Run Condenser Agent** with:
   ```json
   {"application_id": "a0000001-1111-2222-3333-444444444444"}
   ```

2. **Run Legal Search Agent** with:
   ```json
   {"application_id": "a0000001-1111-2222-3333-444444444444"}
   ```

**Expected Result**: INVALID - Grantor exceeds authority

## Test Case: Hamza Awad

The repository includes a pre-configured test case to validate the system:

| Field | Value |
|-------|-------|
| **Application** | SAK-2026-POA-TEST001 |
| **Grantor** | Hamza Awad (Canadian) |
| **Agent** | Hussein Motaz (Qatari) |
| **Company** | Sola Services (CR #3333) |
| **Grantor's CR Authority** | "Passports" only |
| **POA Grants** | Full management, contracts, govt representation |
| **Expected Verdict** | **INVALID** |

### Why INVALID?

Per Qatari Civil Code Article 2:
> "The principal may not grant the agent rights or authorities exceeding what the principal himself possesses."

Hamza's CR shows he only has "Passports" authority, but the POA attempts to grant full management powers. This exceeds his legal authority.

## Project Structure

```
test_agents/
├── README.md                           # This file
├── migrations/
│   ├── 001_new_data_model.sql          # Full database schema (27 tables)
│   ├── 002_seed_test_case.sql          # Test case + legal articles
│   └── 003_generate_embeddings.py      # Embedding generation script
├── poa_agents/
│   ├── condenser_agent/
│   │   ├── README.md                   # Agent documentation
│   │   ├── .env                        # Environment variables
│   │   ├── manifest.yaml               # Agentex configuration
│   │   └── project/
│   │       ├── acp.py                  # Main handler
│   │       ├── llm_client.py           # OpenAI client
│   │       └── supabase_client.py      # Database client
│   ├── legal_search_agent/
│   │   ├── README.md                   # Agent documentation
│   │   ├── .env                        # Environment variables
│   │   ├── manifest.yaml               # Agentex configuration
│   │   └── project/
│   │       ├── acp.py                  # Main handler
│   │       ├── llm_client.py           # OpenAI + Embeddings client
│   │       ├── supabase_client.py      # Database + RAG client
│   │       └── components/
│   │           ├── decomposer.py       # Issue decomposition
│   │           ├── retriever.py        # RAG search
│   │           └── synthesizer.py      # Opinion synthesis
│   └── shared/                         # Shared utilities
└── tier1_validation_agent/             # (Future) Tier 1 validation
```

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `applications` | POA/Sale application records |
| `parties` | Grantor, agent, and other parties |
| `capacity_proofs` | Evidence of authority (CR, POA) |
| `documents` | Uploaded documents |
| `document_extractions` | OCR results from documents |

### ML Pipeline Tables

| Table | Purpose |
|-------|---------|
| `legal_briefs` | Condenser Agent output |
| `legal_opinions` | Legal Search Agent output |
| `articles` | Legal corpus with embeddings |

### Key Function

```sql
-- Semantic search over legal articles
match_articles(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    language text  -- 'arabic' or 'english'
)
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Agent Framework** | Agentex (FastACP) |
| **LLM** | OpenAI GPT-4o-mini |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dim) |
| **Database** | Supabase (PostgreSQL) |
| **Vector Search** | pgvector extension |
| **Language** | Python 3.12 |

## RAG Configuration

### Embedding Strategy

- **Corpus Language**: Arabic legal texts
- **Query Language**: Arabic (for better matching)
- **Embedding Model**: text-embedding-3-small
- **Dimensions**: 1536
- **Similarity Metric**: Cosine distance

### Search Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SIMILARITY_THRESHOLD` | 0.3 | Minimum similarity score |
| `MAX_ARTICLES_PER_ISSUE` | 5 | Max articles per legal issue |

### Improving RAG Quality

1. **Use Arabic queries**: The decomposer generates `search_queries_ar` for optimal matching
2. **Ensure embeddings exist**: Run `003_generate_embeddings.py` after adding articles
3. **Tune threshold**: Lower threshold returns more results (may include noise)
4. **Check similarity scores**: >70% is excellent, 50-70% is good, 30-50% is fair

## Outputs

### Condenser Agent Output

```
# Legal Brief
**Application ID:** a0000001-1111-2222-3333-444444444444

## Parties
### GRANTOR
- **Name:** Hamza Awad / حمزة عوض
- **Capacity Claimed:** Manager with full authority
- **Capacity Evidence:** CR shows: Manager (Passports only)

## Fact Discrepancies Detected
### Grantor Authority
- **POA text:** Full management powers
- **CR extract:** Passports only
- **Notes:** CRITICAL MISMATCH
```

### Legal Search Agent Output

```
# ❌ Legal Research Opinion

## Decision
### ❌ Finding: **INVALID**
### Confidence: **85%** (HIGH)

## Opinion Summary
The POA is INVALID because the grantor is attempting to delegate
powers he does not possess per the Commercial Registry...

## Legal Citations
### Article 2
> The principal may not grant the agent rights or authorities
> exceeding what the principal himself possesses...
*Similarity: 72%*
```

## Development

### Adding New Legal Articles

1. Insert into `articles` table with Arabic and English text
2. Run embedding generation:
   ```python
   python migrations/003_generate_embeddings.py
   ```
3. Verify with similarity search in Supabase

### Testing RAG Quality

Check the similarity scores in Legal Search Agent output:
- Articles with >70% similarity indicate strong semantic matches
- If scores are consistently low, review the Arabic search queries

### Debugging

Each agent logs extensively:
```bash
# View agent logs
agentex dev  # Logs appear in terminal
```

Key log points:
- LLM prompts and responses
- Semantic search queries and results
- Database operations

## License

Internal use only. Part of the SAK AI Project.
