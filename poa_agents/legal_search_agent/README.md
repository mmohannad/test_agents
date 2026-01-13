# Legal Search Agent

The Legal Search Agent performs **statute-grounded legal research** on POA applications using RAG (Retrieval-Augmented Generation) to determine validity based on Qatari civil and commercial law.

## Overview

This is the Tier 2 agent in the SAK AI validation pipeline. It takes a Legal Brief from the Condenser Agent and:
1. **Decomposes** the case into specific legal sub-issues
2. **Retrieves** relevant legal articles using semantic search (Arabic embeddings)
3. **Synthesizes** a comprehensive legal opinion with citations
4. **Determines** validity: VALID, INVALID, VALID_WITH_CONDITIONS, or NEEDS_REVIEW

```
Legal Brief  →  [Decomposer]  →  [Retriever (RAG)]  →  [Synthesizer]  →  Legal Opinion
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
│   └── components/
│       ├── __init__.py
│       ├── decomposer.py   # Breaks case into legal issues
│       ├── retriever.py    # RAG search for articles
│       └── synthesizer.py  # Generates legal opinion
```

## RAG Pipeline

### Phase 1: Decomposition

The Decomposer analyzes the Legal Brief and generates legal sub-issues:

```json
{
  "issue_id": "ISSUE_1",
  "category": "grantor_capacity",
  "primary_question": "Does the grantor have authority to delegate these powers?",
  "sub_questions": [
    "What is the grantor's authority scope per the Commercial Registry?",
    "Can a manager with limited authority delegate broader powers?"
  ],
  "relevant_facts": [
    "Grantor is Manager (Passports only)",
    "POA grants full management powers"
  ],
  "search_queries_ar": [
    "لا يجوز للموكل أن يمنح الوكيل صلاحيات تزيد عما يملكه",
    "حدود الوكالة",
    "أهلية الموكل في الوكالة"
  ],
  "priority": 1
}
```

**Key Feature**: Search queries are generated in **Arabic** (`search_queries_ar`) for optimal semantic matching against the Arabic legal corpus.

### Phase 2: Retrieval (RAG)

The Retriever performs semantic search using:
- **Embedding Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Vector Database**: Supabase with pgvector extension
- **Search Function**: `match_articles` RPC with cosine similarity
- **Similarity Threshold**: 0.3 (configurable)
- **Max Articles**: 5 per issue (configurable)

```sql
-- The match_articles function uses Arabic embeddings
SELECT article_number, text_arabic, text_english,
       1 - (arabic_embedding <=> query_embedding) as similarity
FROM articles
WHERE similarity > threshold
ORDER BY similarity DESC
LIMIT 5;
```

### Phase 3: Synthesis

The Synthesizer generates a comprehensive legal opinion:

```json
{
  "overall_finding": "INVALID",
  "confidence_score": 0.85,
  "confidence_level": "HIGH",
  "decision_bucket": "invalid",
  "opinion_summary_en": "The POA is INVALID because the grantor (Hamza Awad) is attempting to delegate powers he does not possess...",
  "opinion_summary_ar": "الوكالة باطلة لأن الموكل (حمزة عوض) يحاول تفويض صلاحيات لا يملكها...",
  "findings": [
    {
      "issue_id": "ISSUE_1",
      "finding": "NOT_SUPPORTED",
      "confidence": 0.9,
      "reasoning": "Per Article 2 of Civil Code, a principal cannot grant more authority than they possess..."
    }
  ],
  "all_citations": [
    {
      "article_number": 2,
      "text_english": "The principal may not grant the agent rights or authorities exceeding...",
      "similarity": 0.716
    }
  ],
  "concerns": [
    "Grantor's CR authority is 'Passports' but POA grants full management"
  ],
  "recommendations": [
    "Reject this POA application",
    "Require POA from authorized manager with full authority"
  ]
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
    "poa_details": {...},
    "open_questions": [...]
  }
}
```

### Output: Legal Opinion

The agent produces:
1. **Formatted Display** - Markdown with verdict, analysis, citations
2. **JSON Storage** - Full opinion saved to `legal_opinions` table

#### UI Display Format

```markdown
# ❌ Legal Research Opinion

**Application ID:** a0000001-1111-2222-3333-444444444444
**Generated:** 2026-01-13T12:00:00

---

## Decision

### ❌ Finding: **INVALID**
### Decision Bucket: **INVALID**
### Confidence: **85%** (HIGH)

---

## Opinion Summary

The Power of Attorney is INVALID. The grantor, Hamza Awad, holds only
"Passports" authority per the Commercial Registry, but is attempting
to grant the agent (Hussein Motaz) full management powers including
contract signing and government representation...

---

## Legal Citations

### Article 2
*Civil Code - Agency*
> The principal may not grant the agent rights or authorities exceeding
> what the principal himself possesses in terms of legal rights or capacity...
*Similarity: 72%*
```

## Environment Variables

Create a `.env` file in the agent directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...your-key...
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

### Using the Agentex UI

1. Open the Agentex UI (typically `http://localhost:3000`)
2. Select "legal-search-agent" from the agent list
3. Send a message with the application ID:
   ```json
   {"application_id": "a0000001-1111-2222-3333-444444444444"}
   ```
4. The agent will respond with the legal opinion

### End-to-End Test

```bash
# 1. Run Condenser Agent first to create Legal Brief
# In Agentex UI, select condenser-agent:
{"application_id": "a0000001-1111-2222-3333-444444444444"}

# 2. Then run Legal Search Agent
# In Agentex UI, select legal-search-agent:
{"application_id": "a0000001-1111-2222-3333-444444444444"}
```

## Database Schema

### Input Tables

#### `legal_briefs`
Created by Condenser Agent:
- `brief_content` (JSONB) - Structured case facts
- `issues_to_analyze` - Open questions for research

#### `articles`
Legal corpus with embeddings:
- `article_number` - Primary key
- `text_arabic` - Arabic article text
- `text_english` - English translation
- `embedding` - English embedding (vector 1536)
- `arabic_embedding` - Arabic embedding (vector 1536)
- `hierarchy_path` - Law/chapter/section structure

### Output Tables

#### `legal_opinions`
Stores the research results:
- `finding` - VALID, INVALID, etc.
- `confidence_score` - 0.0 to 1.0
- `summary_ar`, `summary_en` - Opinion summaries
- `full_analysis` (JSONB) - Complete opinion
- `legal_citations` (JSONB) - Referenced articles
- `grounding_score` - How well-grounded in citations

### `match_articles` RPC Function

```sql
CREATE FUNCTION match_articles(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    language text DEFAULT 'english'
) RETURNS TABLE (
    article_number integer,
    hierarchy_path jsonb,
    text_arabic text,
    text_english text,
    similarity float
)
```

Uses dynamic SQL to select either `embedding` (English) or `arabic_embedding` (Arabic) based on the `language` parameter.

## Component Details

### Decomposer (`components/decomposer.py`)

- **Purpose**: Break Legal Brief into researchable legal issues
- **LLM Model**: GPT-4o-mini (temperature: 0.2)
- **Output**: List of issues with Arabic search queries
- **Key Feature**: Generates search queries in Arabic for better RAG matching

### Retriever (`components/retriever.py`)

- **Purpose**: Find relevant articles using semantic search
- **Search Strategy**: Uses Arabic queries against Arabic embeddings
- **Deduplication**: By article number, keeps highest similarity
- **Fallback**: If semantic search fails, returns top N active articles

### Synthesizer (`components/synthesizer.py`)

- **Purpose**: Generate comprehensive legal opinion from evidence
- **LLM Model**: GPT-4o-mini (temperature: 0.2, max_tokens: 4000)
- **Citation Requirements**: Every conclusion must cite specific articles
- **Output Languages**: English + Arabic summaries

## Verification Metrics

The agent calculates several quality metrics:

| Metric | Description |
|--------|-------------|
| `grounding_score` | % of findings supported by article citations |
| `retrieval_coverage` | % of issues with retrieved evidence |
| `confidence_score` | Overall confidence in the verdict |

## Decision Buckets

| Bucket | Meaning |
|--------|---------|
| `valid` | POA is legally valid, can proceed |
| `valid_with_remediations` | Valid if conditions are met |
| `invalid` | POA is legally invalid, must reject |
| `needs_review` | Insufficient evidence, requires SME |

## Error Handling

- Missing Legal Brief returns guidance to run Condenser first
- Failed semantic search falls back to keyword-based retrieval
- JSON parsing errors return partial analysis with raw LLM output
- All errors are logged with full stack traces

## Development

### Key Files

| File | Purpose |
|------|---------|
| `acp.py` | Orchestrates 4-phase pipeline, formats output |
| `decomposer.py` | LLM prompts for issue generation |
| `retriever.py` | RAG search with Arabic embeddings |
| `synthesizer.py` | LLM prompts for opinion generation |
| `llm_client.py` | OpenAI client for chat + embeddings |
| `supabase_client.py` | Database queries + semantic search |

### Testing RAG Quality

Check similarity scores in the output:
- **> 70%**: Excellent match (high confidence)
- **50-70%**: Good match (moderate confidence)
- **30-50%**: Fair match (low confidence)
- **< 30%**: Below threshold (not returned)

### Improving RAG Results

1. Use Arabic search queries (already implemented)
2. Ensure articles have Arabic embeddings populated
3. Tune similarity threshold based on corpus size
4. Consider re-ranking with cross-encoder
