# Deep Research: Advanced RAG for Legal Document Retrieval

## Executive Summary

This document outlines the evolution of our Legal Search Agent's retrieval system from basic semantic search to a sophisticated, production-grade RAG pipeline. We address two phases:

1. **Immediate Implementation**: HyDE + Agentic RAG Loop (Arabic-first)
2. **Future Roadmap**: Ontology-driven Graph-based RAG

The goal is to achieve **statute-grounded legal reasoning** where every conclusion is traceable to specific legal articles with high confidence.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Problem Statement](#2-problem-statement)
3. [Phase 1: HyDE + Agentic RAG Implementation](#3-phase-1-hyde--agentic-rag-implementation)
4. [Iteration Strategy & End Conditions](#4-iteration-strategy--end-conditions)
5. [Evaluation Artifacts](#5-evaluation-artifacts)
6. [Agent Architecture Changes](#6-agent-architecture-changes)
7. [Phase 2: Ontology & Graph-Based RAG Roadmap](#7-phase-2-ontology--graph-based-rag-roadmap)
8. [Industry Landscape](#8-industry-landscape)
9. [Implementation Plan](#9-implementation-plan)
10. [Appendix](#10-appendix)

---

## 1. Current State Analysis

### 1.1 Current Pipeline

```
Legal Brief
    → Decomposer (LLM generates Arabic queries)
    → Retriever (embed query → vector search → top-K articles)
    → Synthesizer (LLM generates opinion)
    → Legal Opinion
```

### 1.2 Current Capabilities

| Component | Implementation | Limitations |
|-----------|---------------|-------------|
| **Decomposition** | LLM-generated queries | Unstructured, no coverage guarantee |
| **Embedding** | text-embedding-3-small (1536d) | Query-document semantic gap |
| **Search** | pgvector cosine similarity | Single-hop, no cross-references |
| **Retrieval** | Top-5 per query, deduplication | No verification, no iteration |
| **Synthesis** | Single LLM pass | No citation verification |

### 1.3 Corpus Characteristics

- **~9,000 articles** from Qatari Civil and Commercial Code
- **Per-article embeddings** (no chunking, articles are coherent units)
- **Dual language**: Arabic source + English translation
- **Hierarchical structure**: Book → Chapter → Section → Article
- **Cross-references**: Articles frequently reference other articles

### 1.4 Observed Issues

1. **Similarity scores plateau at 60-75%** even for highly relevant articles
2. **Missing related articles** that are referenced but not retrieved
3. **Inconsistent coverage** of legal areas
4. **No verification** that retrieved evidence is sufficient

---

## 2. Problem Statement

### 2.1 The Query-Document Semantic Gap

**The core problem**: User questions and legal articles exist in different semantic spaces.

```
Query (Question Space):
"Can a manager with limited authority grant broader powers to an agent?"

Article (Legal Statement Space):
"لا يجوز للموكل أن يمنح الوكيل حقوقاً أو صلاحيات تزيد عما يملكه الموكل نفسه"
(The principal may not grant the agent rights or authorities exceeding
what the principal himself possesses)
```

Even when the article is **exactly** what we need, the embedding similarity may be mediocre because:
- Questions use interrogative framing
- Articles use declarative/prescriptive framing
- Different vocabulary (colloquial vs. legal)
- Conceptual overlap ≠ lexical overlap

### 2.2 Single-Hop Limitation

Legal reasoning is inherently **multi-hop**:

```
User Question: "Is Hamza's POA valid?"
                    ↓
Article 2: "Principal cannot delegate beyond own authority"
                    ↓
References Article 6: "Authority is determined by commercial register"
                    ↓
References Article 721: "Manager authorities in companies"
                    ↓
Complete answer requires all three articles
```

Current system retrieves only the first hop based on query similarity.

### 2.3 No Coverage Guarantee

The LLM generates queries based on intuition, not legal expertise. For POA validation, we need coverage of:

- [ ] Agency law (الوكالة)
- [ ] Capacity requirements (الأهلية)
- [ ] Delegation limits (حدود التفويض)
- [ ] Commercial registration (السجل التجاري)
- [ ] Formalities (الشكليات)

Current system has no mechanism to verify all areas are covered.

---

## 3. Phase 1: HyDE + Agentic RAG Implementation

### 3.1 HyDE (Hypothetical Document Embeddings)

#### Concept

Instead of embedding the **query**, we ask the LLM to generate a **hypothetical legal article** that would answer the question, then search for real articles similar to that hypothetical.

```
┌─────────────────────────────────────────────────────────────────┐
│                        HyDE PROCESS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Legal Question                                                  │
│  "هل يجوز للمدير ذو الصلاحيات المحدودة منح صلاحيات أوسع؟"        │
│                     ↓                                            │
│  LLM generates hypothetical article (Arabic)                     │
│                     ↓                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ "المادة (هـ): لا يجوز للمدير المقيد الصلاحيات بموجب      │    │
│  │ السجل التجاري أن يفوض غيره صلاحيات تتجاوز نطاق ما هو     │    │
│  │ مخول له. وكل تفويض يتجاوز هذه الحدود يعتبر باطلاً        │    │
│  │ ولا يرتب أي أثر قانوني على الموكل أو الشركة."            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                     ↓                                            │
│  Embed this hypothetical                                         │
│                     ↓                                            │
│  Search for similar REAL articles                                │
│                     ↓                                            │
│  Retrieved: Article 2, Article 6, Article 721                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Arabic?

1. **Corpus is Arabic**: The legal articles are in Arabic, embeddings are generated from Arabic text
2. **Client operates in Arabic**: End users query in Arabic
3. **Semantic space alignment**: Arabic hypothetical → Arabic embeddings = same semantic space
4. **Model capability**: text-embedding-3-small handles Arabic well

#### HyDE Prompt Design

```python
HYDE_SYSTEM_PROMPT = """أنت خبير في صياغة المواد القانونية القطرية.
مهمتك: تحويل السؤال القانوني إلى مادة قانونية افتراضية.

قواعد الصياغة:
1. ابدأ بـ "المادة (X):"
2. استخدم الأسلوب التقريري القانوني (لا يجوز، يجب، يحق)
3. اجعل المادة موجزة (فقرة إلى فقرتين)
4. استخدم المصطلحات القانونية الصحيحة
5. لا تخترع أرقام مواد حقيقية

المادة الافتراضية يجب أن تكون كما لو كانت موجودة في القانون المدني القطري."""

HYDE_USER_TEMPLATE = """السؤال القانوني: {question}

اكتب مادة قانونية افتراضية تجيب على هذا السؤال:"""
```

#### HyDE Risk Mitigation

**Risk**: LLM generates legally incorrect hypothetical → retrieves wrong articles

**Mitigations**:
1. **Multiple hypotheticals**: Generate 2-3 hypotheticals per question, search with all
2. **Confidence weighting**: Weight results by consistency across hypotheticals
3. **Fallback to direct search**: If hypothetical similarity < 0.4, fall back to query embedding
4. **Human-in-the-loop for edge cases**: Flag low-confidence retrievals for review

### 3.2 Agentic RAG Loop

#### Concept

Replace one-shot retrieval with an **iterative agent** that:
1. Retrieves articles
2. Analyzes coverage gaps
3. Generates targeted queries for gaps
4. Repeats until sufficient

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC RAG LOOP                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ITERATION 1: Initial Retrieval                                  │
│  ├─ Generate HyDE hypotheticals for each decomposed issue        │
│  ├─ Retrieve top-K articles per hypothetical                     │
│  ├─ Deduplicate and rank                                         │
│  └─ Agent analyzes: "What legal areas are covered?"              │
│                     ↓                                            │
│  Coverage Check:                                                 │
│  ✓ Agency law (3 articles, avg similarity 0.72)                  │
│  ✓ Capacity (2 articles, avg similarity 0.65)                    │
│  ✗ Commercial registration (0 articles) ← GAP                    │
│  ✗ Formalities (1 article, avg similarity 0.35) ← WEAK           │
│                     ↓                                            │
│  ITERATION 2: Gap-Filling                                        │
│  ├─ Agent generates targeted queries for gaps:                   │
│  │   "صلاحيات المدير في السجل التجاري"                           │
│  │   "شروط شكلية الوكالة"                                        │
│  ├─ HyDE + retrieval for new queries                             │
│  └─ Merge with existing results                                  │
│                     ↓                                            │
│  Coverage Check:                                                 │
│  ✓ Agency law (3 articles)                                       │
│  ✓ Capacity (2 articles)                                         │
│  ✓ Commercial registration (2 articles) ← FILLED                 │
│  ✓ Formalities (2 articles) ← IMPROVED                           │
│                     ↓                                            │
│  ITERATION 3: Cross-Reference Expansion                          │
│  ├─ Parse all retrieved articles for references                  │
│  │   Found: "المادة 5", "المادة 721", "المادة 12"                 │
│  ├─ Fetch referenced articles directly                           │
│  └─ Add to result set                                            │
│                     ↓                                            │
│  END CONDITION MET: Coverage complete + references expanded      │
│                     ↓                                            │
│  Final Article Set → Synthesizer                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Agent State

```python
@dataclass
class RetrievalState:
    """State maintained across iterations."""
    iteration: int
    articles: dict[int, ArticleWithMetadata]  # article_number → article
    coverage: dict[str, CoverageStatus]       # legal_area → status
    queries_tried: list[str]                  # avoid repeating queries
    cross_refs_fetched: set[int]              # already fetched references

    # Metrics for eval
    iteration_logs: list[IterationLog]
    total_llm_calls: int
    total_embedding_calls: int
    total_latency_ms: int

@dataclass
class CoverageStatus:
    area_name: str
    area_name_ar: str
    keywords: list[str]
    required: bool
    articles_found: list[int]
    avg_similarity: float
    status: Literal["covered", "weak", "missing"]
```

---

## 4. Iteration Strategy & End Conditions

### 4.1 Why Limit Iterations?

| Iterations | Latency | Cost | Quality |
|------------|---------|------|---------|
| 1 | ~2s | $ | 60-70% coverage |
| 2 | ~4s | $$ | 85-90% coverage |
| 3 | ~6s | $$$ | 92-95% coverage |
| 4+ | ~8s+ | $$$$ | Diminishing returns |

**Industry consensus**: 2-3 iterations is optimal. Beyond that:
- Latency becomes unacceptable for interactive use
- LLM costs increase linearly
- Coverage improvements plateau
- Risk of retrieving tangentially related but unhelpful articles

### 4.2 Iteration Purposes

Each iteration has a specific purpose:

| Iteration | Purpose | Actions |
|-----------|---------|---------|
| **1** | Broad retrieval | HyDE for all decomposed issues |
| **2** | Gap filling | Targeted queries for missing areas |
| **3** | Reference expansion | Fetch cross-referenced articles |

### 4.3 End Conditions (Detailed)

The agent should stop when **ANY** of these conditions is met:

#### Condition 1: Coverage Threshold Met

```python
REQUIRED_LEGAL_AREAS = {
    "agency_law": {
        "keywords_ar": ["وكالة", "موكل", "وكيل", "تفويض"],
        "keywords_en": ["agency", "principal", "agent", "delegation"],
        "required": True,
        "min_articles": 1,
        "min_avg_similarity": 0.5
    },
    "capacity": {
        "keywords_ar": ["أهلية", "صلاحية", "سلطة"],
        "keywords_en": ["capacity", "authority", "competence"],
        "required": True,
        "min_articles": 1,
        "min_avg_similarity": 0.5
    },
    "delegation_limits": {
        "keywords_ar": ["حدود", "نطاق", "تجاوز", "يزيد عما"],
        "keywords_en": ["limits", "scope", "exceed", "beyond"],
        "required": True,
        "min_articles": 1,
        "min_avg_similarity": 0.5
    },
    "commercial_registration": {
        "keywords_ar": ["سجل تجاري", "شركة", "مدير"],
        "keywords_en": ["commercial register", "company", "manager"],
        "required": False,  # Only if case involves company
        "min_articles": 1,
        "min_avg_similarity": 0.4
    },
    "formalities": {
        "keywords_ar": ["شكل", "توثيق", "كتابة"],
        "keywords_en": ["form", "notarization", "writing"],
        "required": False,
        "min_articles": 1,
        "min_avg_similarity": 0.4
    }
}

def check_coverage(articles: list[dict], case_type: str) -> tuple[bool, dict]:
    """Check if required legal areas are covered."""
    coverage = {}
    for area, config in REQUIRED_LEGAL_AREAS.items():
        # Skip non-required areas for this case type
        if not config["required"] and not is_relevant_to_case(area, case_type):
            continue

        matching_articles = find_articles_matching_area(articles, config["keywords_ar"])
        avg_sim = calculate_avg_similarity(matching_articles)

        coverage[area] = {
            "articles": matching_articles,
            "avg_similarity": avg_sim,
            "status": "covered" if (
                len(matching_articles) >= config["min_articles"] and
                avg_sim >= config["min_avg_similarity"]
            ) else "weak" if matching_articles else "missing"
        }

    all_required_covered = all(
        coverage[area]["status"] == "covered"
        for area in coverage
        if REQUIRED_LEGAL_AREAS[area]["required"]
    )

    return all_required_covered, coverage
```

#### Condition 2: Confidence Threshold Met

```python
def check_confidence(articles: list[dict]) -> bool:
    """Check if overall retrieval confidence is sufficient."""
    if len(articles) < 3:
        return False

    similarities = [a["similarity"] for a in articles]
    avg_similarity = sum(similarities) / len(similarities)
    top_3_avg = sum(sorted(similarities, reverse=True)[:3]) / 3

    return (
        avg_similarity >= 0.55 and  # Overall average
        top_3_avg >= 0.65 and       # Top articles are strong
        len(articles) >= 5          # Minimum article count
    )
```

#### Condition 3: Agent Self-Assessment

```python
SELF_ASSESSMENT_PROMPT = """أنت محلل قانوني تقيّم مدى كفاية الأدلة القانونية.

السؤال القانوني الأصلي:
{original_question}

المواد القانونية المسترجعة:
{articles_summary}

المجالات القانونية المغطاة:
{coverage_summary}

هل لديك أدلة كافية للإجابة على السؤال القانوني بثقة؟

أجب بصيغة JSON:
{{
    "sufficient": true/false,
    "confidence": 0.0-1.0,
    "missing_areas": ["area1", "area2"],
    "reasoning": "..."
}}"""
```

#### Condition 4: Hard Limits (Circuit Breakers)

```python
HARD_LIMITS = {
    "max_iterations": 3,
    "max_articles": 30,
    "max_llm_calls": 15,
    "max_latency_ms": 30000,  # 30 seconds
    "max_embedding_calls": 50
}

def check_hard_limits(state: RetrievalState) -> bool:
    """Check if any hard limit is reached."""
    return (
        state.iteration >= HARD_LIMITS["max_iterations"] or
        len(state.articles) >= HARD_LIMITS["max_articles"] or
        state.total_llm_calls >= HARD_LIMITS["max_llm_calls"] or
        state.total_latency_ms >= HARD_LIMITS["max_latency_ms"]
    )
```

#### Combined End Condition Logic

```python
def should_stop(state: RetrievalState, case_type: str) -> tuple[bool, str]:
    """Determine if retrieval should stop."""

    # Hard limits always take precedence
    if check_hard_limits(state):
        return True, "hard_limit_reached"

    articles = list(state.articles.values())

    # Check coverage
    coverage_met, coverage_details = check_coverage(articles, case_type)
    if coverage_met:
        return True, "coverage_threshold_met"

    # Check confidence
    if check_confidence(articles):
        return True, "confidence_threshold_met"

    # Agent self-assessment (only after iteration 2)
    if state.iteration >= 2:
        assessment = agent_self_assess(state)
        if assessment["sufficient"] and assessment["confidence"] >= 0.7:
            return True, "agent_self_assessment_sufficient"

    # Diminishing returns check
    if state.iteration >= 2:
        new_articles_this_iteration = count_new_articles(state)
        if new_articles_this_iteration <= 1:
            return True, "diminishing_returns"

    return False, "continue"
```

### 4.4 Iteration Decision Tree

```
START
  │
  ├─ Iteration 1: Broad Retrieval
  │   ├─ Generate HyDE hypotheticals
  │   ├─ Retrieve articles
  │   └─ Check end conditions
  │       ├─ Coverage met? → STOP
  │       ├─ Confidence met? → STOP
  │       └─ Continue
  │
  ├─ Iteration 2: Gap Filling
  │   ├─ Identify missing areas
  │   ├─ Generate targeted queries
  │   ├─ Retrieve additional articles
  │   └─ Check end conditions
  │       ├─ Coverage met? → STOP
  │       ├─ Confidence met? → STOP
  │       ├─ Agent says sufficient? → STOP
  │       └─ Continue
  │
  └─ Iteration 3: Reference Expansion
      ├─ Parse cross-references
      ├─ Fetch referenced articles
      └─ STOP (max iterations)
```

---

## 5. Evaluation Artifacts

### 5.1 Why Save Artifacts?

To enable:
1. **Regression testing**: Did the new version retrieve better articles?
2. **Failure analysis**: Why did case X get wrong verdict?
3. **Coverage tracking**: Are we improving over time?
4. **Cost optimization**: How many LLM calls per case?
5. **SME review**: Show domain experts what the system retrieved

### 5.2 Artifact Schema

#### Per-Case Retrieval Log

```python
@dataclass
class RetrievalEvalArtifact:
    """Complete retrieval log for a single case."""

    # Case identification
    case_id: str
    application_id: str
    timestamp: datetime

    # Input
    legal_brief: dict
    decomposed_issues: list[dict]

    # Per-iteration details
    iterations: list[IterationArtifact]

    # Final output
    final_articles: list[ArticleArtifact]
    final_coverage: dict[str, CoverageStatus]

    # End condition
    stop_reason: str
    stop_iteration: int

    # Metrics
    total_latency_ms: int
    total_llm_calls: int
    total_embedding_calls: int
    total_tokens_used: int
    estimated_cost_usd: float

    # Quality metrics
    avg_similarity: float
    coverage_score: float  # % of required areas covered

    # Downstream result (filled after synthesis)
    verdict: Optional[str]
    verdict_correct: Optional[bool]  # If ground truth available

@dataclass
class IterationArtifact:
    """Details for a single iteration."""

    iteration_number: int
    purpose: str  # "broad_retrieval", "gap_filling", "reference_expansion"

    # Queries
    queries_generated: list[QueryArtifact]

    # Coverage before/after
    coverage_before: dict[str, str]
    coverage_after: dict[str, str]
    gaps_identified: list[str]

    # Articles
    articles_retrieved: list[int]
    articles_new: list[int]

    # Timing
    latency_ms: int
    llm_calls: int

    # Agent reasoning (if applicable)
    agent_reasoning: Optional[str]

@dataclass
class QueryArtifact:
    """Details for a single query."""

    query_type: str  # "direct", "hyde_hypothetical"
    query_text: str
    query_language: str

    # If HyDE
    hypothetical_generated: Optional[str]

    # Results
    articles_found: list[int]
    similarities: list[float]

    # Timing
    embedding_latency_ms: int
    search_latency_ms: int

@dataclass
class ArticleArtifact:
    """Article with retrieval metadata."""

    article_number: int
    text_arabic: str
    text_english: str
    hierarchy_path: dict

    # Retrieval info
    found_by_query: str
    found_in_iteration: int
    similarity: float

    # Cross-reference info
    is_cross_reference: bool
    referenced_by: Optional[int]

    # Coverage info
    matched_legal_areas: list[str]
```

### 5.3 Storage Schema (Supabase)

```sql
-- Retrieval evaluation logs
CREATE TABLE retrieval_eval_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Input
    legal_brief JSONB,
    decomposed_issues JSONB,

    -- Full artifact (compressed)
    artifact JSONB,

    -- Summary metrics (for querying)
    total_iterations INT,
    stop_reason VARCHAR(50),
    total_articles INT,
    avg_similarity DECIMAL(4,3),
    coverage_score DECIMAL(4,3),
    total_latency_ms INT,
    total_llm_calls INT,
    estimated_cost_usd DECIMAL(10,4),

    -- Result
    verdict VARCHAR(30),
    verdict_correct BOOLEAN,

    -- Version tracking
    agent_version VARCHAR(50),
    retrieval_config JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_retrieval_logs_app ON retrieval_eval_logs(application_id);
CREATE INDEX idx_retrieval_logs_verdict ON retrieval_eval_logs(verdict);
CREATE INDEX idx_retrieval_logs_coverage ON retrieval_eval_logs(coverage_score);
```

### 5.4 Evaluation Queries

```sql
-- Cases with low coverage
SELECT application_id, coverage_score, stop_reason, verdict
FROM retrieval_eval_logs
WHERE coverage_score < 0.7
ORDER BY created_at DESC;

-- Average metrics by verdict
SELECT verdict,
       AVG(avg_similarity) as avg_sim,
       AVG(total_iterations) as avg_iters,
       AVG(total_latency_ms) as avg_latency
FROM retrieval_eval_logs
GROUP BY verdict;

-- Retrieval quality over time
SELECT DATE(created_at) as date,
       AVG(coverage_score) as avg_coverage,
       AVG(avg_similarity) as avg_similarity
FROM retrieval_eval_logs
GROUP BY DATE(created_at)
ORDER BY date;
```

---

## 6. Agent Architecture Changes

### 6.1 Current vs. New Architecture

```
CURRENT:
┌─────────────┐     ┌───────────┐     ┌─────────────┐
│ Decomposer  │ ──> │ Retriever │ ──> │ Synthesizer │
│ (1 LLM call)│     │(N embeds) │     │ (1 LLM call)│
└─────────────┘     └───────────┘     └─────────────┘

NEW:
┌─────────────┐     ┌──────────────────────────────────┐     ┌─────────────┐
│ Decomposer  │ ──> │      Agentic Retriever           │ ──> │ Synthesizer │
│ (1 LLM call)│     │  ┌─────────────────────────────┐ │     │ (1 LLM call)│
└─────────────┘     │  │ HyDE Generator (N LLM calls)│ │     └─────────────┘
                    │  └─────────────────────────────┘ │
                    │  ┌─────────────────────────────┐ │
                    │  │ Vector Search (M embeds)    │ │
                    │  └─────────────────────────────┘ │
                    │  ┌─────────────────────────────┐ │
                    │  │ Coverage Analyzer (K calls) │ │
                    │  └─────────────────────────────┘ │
                    │  ┌─────────────────────────────┐ │
                    │  │ Cross-Ref Expander (direct) │ │
                    │  └─────────────────────────────┘ │
                    └──────────────────────────────────┘
```

### 6.2 New Component: HyDE Generator

```
project/components/
├── decomposer.py         # Existing
├── retriever.py          # Modified
├── synthesizer.py        # Existing
├── hyde_generator.py     # NEW
├── coverage_analyzer.py  # NEW
├── crossref_expander.py  # NEW
└── retrieval_agent.py    # NEW - Orchestrates the loop
```

### 6.3 Component Responsibilities

| Component | Input | Output | LLM Calls |
|-----------|-------|--------|-----------|
| `hyde_generator.py` | Query | Hypothetical article | 1 per query |
| `coverage_analyzer.py` | Articles | Coverage status | 1 per iteration |
| `crossref_expander.py` | Articles | Referenced article numbers | 0 (regex) |
| `retrieval_agent.py` | Issues | Final article set | Orchestration |

### 6.4 Data Flow

```python
# retrieval_agent.py (pseudo-code)

async def retrieve_with_agent(
    issues: list[dict],
    case_type: str
) -> RetrievalEvalArtifact:
    """Main agentic retrieval loop."""

    state = RetrievalState(iteration=0, articles={}, ...)
    artifact = RetrievalEvalArtifact(...)

    while True:
        state.iteration += 1
        iteration_artifact = IterationArtifact(iteration_number=state.iteration)

        if state.iteration == 1:
            # Broad retrieval with HyDE
            queries = generate_hyde_queries(issues)
            articles = await search_with_hyde(queries)

        elif state.iteration == 2:
            # Gap filling
            gaps = analyze_coverage(state.articles)
            if not gaps:
                break
            queries = generate_gap_queries(gaps)
            articles = await search_with_hyde(queries)

        elif state.iteration == 3:
            # Cross-reference expansion
            refs = extract_cross_references(state.articles)
            articles = await fetch_articles_by_number(refs)

        # Merge new articles
        merge_articles(state, articles)

        # Log iteration
        artifact.iterations.append(iteration_artifact)

        # Check end conditions
        should_stop, reason = check_end_conditions(state, case_type)
        if should_stop:
            artifact.stop_reason = reason
            break

    artifact.final_articles = list(state.articles.values())
    return artifact
```

---

## 7. Phase 2: Ontology & Graph-Based RAG Roadmap

> **Note**: This section outlines the long-term vision requiring SME collaboration. Implementation should begin after Phase 1 is validated.

### 7.1 Vision

Transform from **keyword-based coverage checking** to **ontology-driven legal reasoning** with a **knowledge graph** capturing the structure of Qatari law.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    GRAPH-BASED LEGAL RAG                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  User Query                                                               │
│       ↓                                                                   │
│  ┌─────────────────────────────────────────┐                             │
│  │ Ontology-Based Query Understanding      │                             │
│  │ • Map query to legal concepts           │                             │
│  │ • Identify required legal areas         │                             │
│  │ • Determine transaction type rules      │                             │
│  └─────────────────────────────────────────┘                             │
│       ↓                                                                   │
│  ┌─────────────────────────────────────────┐                             │
│  │ Knowledge Graph Traversal               │                             │
│  │ • Start from concept nodes              │                             │
│  │ • Follow DEFINES, APPLIES_TO edges      │                             │
│  │ • Collect article subgraph              │                             │
│  └─────────────────────────────────────────┘                             │
│       ↓                                                                   │
│  ┌─────────────────────────────────────────┐                             │
│  │ Hybrid Retrieval                        │                             │
│  │ • Graph-retrieved articles              │                             │
│  │ • + Vector similarity articles          │                             │
│  │ • + Ontology-required articles          │                             │
│  └─────────────────────────────────────────┘                             │
│       ↓                                                                   │
│  Complete, Grounded Legal Opinion                                         │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Ontology Structure

#### 7.2.1 Legal Concept Hierarchy

```yaml
Legal_Concepts:
  Agency_Law:
    ar: "الوكالة"
    definition: "Contract whereby principal authorizes agent to act"
    subconcepts:
      - General_Agency:
          ar: "الوكالة العامة"
          article_range: [700-720]
      - Special_Agency:
          ar: "الوكالة الخاصة"
          article_range: [721-740]
      - Capacity:
          ar: "الأهلية"
          subconcepts:
            - Principal_Capacity
            - Agent_Capacity
      - Scope:
          ar: "نطاق الوكالة"
      - Termination:
          ar: "انتهاء الوكالة"

  Commercial_Law:
    ar: "القانون التجاري"
    subconcepts:
      - Companies:
          ar: "الشركات"
          subconcepts:
            - Limited_Liability_Company
            - Joint_Stock_Company
            - Partnership
      - Commercial_Registration:
          ar: "السجل التجاري"
      - Manager_Authority:
          ar: "صلاحيات المدير"

  Contract_Law:
    ar: "قانون العقود"
    subconcepts:
      - Formation
      - Validity
      - Voidability
      - Nullity
```

#### 7.2.2 Transaction Type Rules

```yaml
Transaction_Types:
  POA_Special_Company:
    code: "POA_SPECIAL_COMPANY"
    required_checks:
      - grantor_capacity_verification
      - agent_identity_verification
      - authority_scope_validation
      - delegation_limits_check
      - commercial_registration_check

    required_legal_areas:
      - agency_law:
          importance: critical
          min_articles: 2
      - delegation_limits:
          importance: critical
          min_articles: 1
      - commercial_registration:
          importance: high
          min_articles: 1
      - formalities:
          importance: medium
          min_articles: 1

    decision_rules:
      - if: "grantor_authority < poa_scope"
        then: INVALID
        cite: "Article 2 - Cannot delegate beyond own authority"
      - if: "cr_authority == 'limited' AND poa_scope == 'general'"
        then: INVALID
        cite: "Article 721 - Manager scope restrictions"
```

### 7.3 Knowledge Graph Schema

#### 7.3.1 Node Types

```
┌─────────────────┬────────────────────────────────────────────┐
│ Node Type       │ Properties                                  │
├─────────────────┼────────────────────────────────────────────┤
│ Article         │ number, text_ar, text_en, hierarchy,       │
│                 │ embedding, effective_date                   │
├─────────────────┼────────────────────────────────────────────┤
│ Concept         │ name_ar, name_en, definition,              │
│                 │ parent_concept, level                       │
├─────────────────┼────────────────────────────────────────────┤
│ Entity_Type     │ name (company, individual, government),    │
│                 │ properties                                  │
├─────────────────┼────────────────────────────────────────────┤
│ Legal_Area      │ name, code, description                    │
├─────────────────┼────────────────────────────────────────────┤
│ Transaction     │ type_code, requirements, rules             │
└─────────────────┴────────────────────────────────────────────┘
```

#### 7.3.2 Edge Types

```
┌─────────────────────┬───────────────────────────────────────┐
│ Edge Type           │ Description                           │
├─────────────────────┼───────────────────────────────────────┤
│ REFERENCES          │ Article A cites Article B             │
│ DEFINES             │ Article A defines Concept X           │
│ APPLIES_TO          │ Article A applies to Entity_Type Y    │
│ EXCEPTION_TO        │ Article A is exception to Article B   │
│ EXTENDS             │ Article A extends Article B           │
│ SUPERSEDES          │ Article A supersedes Article B        │
│ BELONGS_TO          │ Article A belongs to Legal_Area Z     │
│ REQUIRES            │ Transaction T requires Legal_Area Z   │
│ PARENT_OF           │ Concept X is parent of Concept Y      │
└─────────────────────┴───────────────────────────────────────┘
```

#### 7.3.3 Example Graph Fragment

```
                    ┌──────────────────┐
                    │  Concept:Agency  │
                    │  الوكالة         │
                    └────────┬─────────┘
                             │ DEFINES
                             ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│  Article 1   │◄───│    Article 2     │───►│  Article 5   │
│  Definition  │    │ Delegation Limit │    │  Capacity    │
│  of Agency   │    │ "cannot exceed"  │    │  Definition  │
└──────────────┘    └────────┬─────────┘    └──────────────┘
                             │ APPLIES_TO
                             ▼
                    ┌──────────────────┐
                    │ Entity: Company  │
                    │ Representative   │
                    └────────┬─────────┘
                             │ REFERENCES
                             ▼
                    ┌──────────────────┐
                    │   Article 721    │
                    │ Manager Powers   │
                    └──────────────────┘
```

### 7.4 Implementation Phases

#### Phase 2.1: Entity & Relationship Extraction (2-3 weeks with SME)

**Goal**: Extract entities and relationships from articles using LLM + SME validation.

```python
# Extraction prompt (conceptual)
EXTRACTION_PROMPT = """تحليل المادة القانونية التالية واستخراج:

1. المفاهيم القانونية المعرّفة
2. المواد المشار إليها (أرقام المواد الأخرى)
3. الاستثناءات المذكورة
4. أنواع الكيانات المشمولة (فرد، شركة، حكومة)

المادة {article_number}:
{article_text}

أجب بصيغة JSON:
{{
    "defines_concepts": [
        {{"concept_ar": "...", "concept_en": "...", "definition_span": [start, end]}}
    ],
    "references_articles": [5, 12, 721],
    "exception_to_articles": [],
    "applies_to_entities": ["company", "individual"],
    "legal_area": "agency_law"
}}"""
```

**Deliverables**:
- Extracted relationships stored in `article_relationships` table
- SME validation interface
- Confidence scores per extraction

#### Phase 2.2: Knowledge Graph Construction (1-2 weeks)

**Goal**: Build Neo4j (or PostgreSQL-based) graph from extracted relationships.

```sql
-- PostgreSQL-based graph tables
CREATE TABLE kg_nodes (
    id UUID PRIMARY KEY,
    node_type VARCHAR(50),  -- article, concept, entity_type
    properties JSONB,
    embedding VECTOR(1536)
);

CREATE TABLE kg_edges (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES kg_nodes(id),
    target_id UUID REFERENCES kg_nodes(id),
    edge_type VARCHAR(50),
    properties JSONB,
    confidence DECIMAL(3,2)
);

CREATE INDEX idx_kg_edges_source ON kg_edges(source_id);
CREATE INDEX idx_kg_edges_target ON kg_edges(target_id);
CREATE INDEX idx_kg_edges_type ON kg_edges(edge_type);
```

**Deliverables**:
- Graph database populated
- Graph visualization for SME review
- Basic traversal queries

#### Phase 2.3: Ontology Development (2-4 weeks with SME)

**Goal**: Define legal ontology with SME collaboration.

**Process**:
1. **Workshop 1**: Identify top 20 legal concepts for POA validation
2. **Workshop 2**: Define concept hierarchy and relationships
3. **Workshop 3**: Map concepts to article ranges
4. **Workshop 4**: Define transaction type rules
5. **Validation**: Test ontology against 50 historical cases

**Deliverables**:
- YAML/JSON ontology definition
- Concept → Article mapping
- Transaction type rule definitions
- Validation report

#### Phase 2.4: Ontology-Driven Retrieval (2-3 weeks)

**Goal**: Integrate ontology into retrieval pipeline.

```python
# Ontology-driven query understanding
def understand_query_with_ontology(
    legal_brief: dict,
    ontology: LegalOntology
) -> QueryUnderstanding:
    """Map query to ontology concepts."""

    # Identify transaction type
    transaction_type = ontology.identify_transaction(legal_brief)

    # Get required legal areas
    required_areas = ontology.get_required_areas(transaction_type)

    # Get concept nodes to start traversal
    entry_concepts = ontology.map_facts_to_concepts(legal_brief["facts"])

    return QueryUnderstanding(
        transaction_type=transaction_type,
        required_areas=required_areas,
        entry_concepts=entry_concepts
    )
```

**Deliverables**:
- `ontology_retriever.py` component
- Integration with agentic loop
- A/B test results vs. non-ontology

#### Phase 2.5: Graph-Augmented Retrieval (2-3 weeks)

**Goal**: Use graph traversal for multi-hop retrieval.

```python
async def graph_augmented_retrieval(
    entry_concepts: list[str],
    max_hops: int = 2
) -> list[Article]:
    """Traverse graph from concepts to articles."""

    # Find concept nodes
    concept_nodes = graph.find_nodes(type="concept", names=entry_concepts)

    # Traverse to articles
    article_nodes = set()
    for concept in concept_nodes:
        # Direct articles
        direct = graph.traverse(concept, edge_type="DEFINES", direction="incoming")
        article_nodes.update(direct)

        # Referenced articles (2nd hop)
        for article in direct:
            refs = graph.traverse(article, edge_type="REFERENCES", direction="outgoing")
            article_nodes.update(refs)

    return list(article_nodes)
```

**Deliverables**:
- `graph_retriever.py` component
- Traversal configuration (max hops, edge types)
- Performance benchmarks

#### Phase 2.6: Hybrid Retrieval & Evaluation (2 weeks)

**Goal**: Combine graph + vector + ontology retrieval.

```python
async def hybrid_retrieval(
    query: str,
    legal_brief: dict,
    ontology: LegalOntology
) -> list[Article]:
    """Combine multiple retrieval strategies."""

    # 1. Ontology-required articles
    required = ontology.get_required_articles(legal_brief)

    # 2. Graph-traversed articles
    concepts = ontology.map_to_concepts(legal_brief)
    graph_articles = await graph_retrieval(concepts)

    # 3. Vector similarity articles (HyDE)
    hyde_articles = await hyde_retrieval(query)

    # Combine and deduplicate
    all_articles = merge_and_rank(required, graph_articles, hyde_articles)

    return all_articles
```

**Deliverables**:
- Hybrid retrieval implementation
- Weighting configuration for each source
- Comprehensive evaluation on test cases

### 7.5 SME Collaboration Requirements

| Phase | SME Time Required | Skills Needed |
|-------|-------------------|---------------|
| 2.1 Entity Extraction | 10-15 hours | Legal domain expert, Arabic |
| 2.3 Ontology Development | 20-30 hours | Senior legal expert, notarization specialist |
| 2.4-2.6 Validation | 10-15 hours | Legal expert, QA mindset |

**Total SME time**: 40-60 hours over 8-12 weeks

### 7.6 Success Metrics for Graph-Based RAG

| Metric | Current | Target (Phase 2) |
|--------|---------|------------------|
| Coverage score | 70-80% | 95%+ |
| Avg similarity | 60-70% | 75%+ |
| Multi-hop retrieval | 0% | 100% of cross-refs |
| Ontology compliance | N/A | 100% required areas |
| SME approval rate | N/A | 90%+ |

---

## 8. Industry Landscape

### 8.1 Academic Research

| Technique | Paper | Key Idea | Relevance |
|-----------|-------|----------|-----------|
| **HyDE** | Gao et al. 2022 | Generate hypothetical doc, embed that | Direct applicability |
| **FLARE** | Jiang et al. 2023 | Forward-looking retrieval, predict when to retrieve | Could enhance our agent |
| **Self-RAG** | Asai et al. 2023 | LLM decides when to retrieve and self-reflects | Aligns with our agent loop |
| **CRAG** | Yan et al. 2024 | Corrective RAG with web fallback | Fallback strategies |
| **GraphRAG** | Microsoft 2024 | Build knowledge graph, community summaries | Our Phase 2 vision |

### 8.2 Industry Implementations

#### LlamaIndex
- **Agentic RAG**: Tool-calling agents that decide retrieval strategy
- **Router Query Engine**: Routes queries to specialized retrievers
- **Recursive Retrieval**: Follows references iteratively

#### LangChain
- **Self-Query Retriever**: LLM generates metadata filters
- **Multi-Query Retriever**: Generates multiple query variants
- **Parent Document Retriever**: Retrieves larger context around matches

#### Microsoft GraphRAG
- **Entity Extraction**: Uses LLM to extract entities and relationships
- **Community Detection**: Clusters related entities
- **Global vs Local Search**: Different strategies for different query types

#### Anthropic (Claude)
- **Contextual Retrieval**: Adds context to chunks before embedding
- **Hybrid Search**: BM25 + semantic search
- **Chunk Optimization**: Recommends 100-300 tokens per chunk

### 8.3 Legal Domain Specific

| System | Approach | Notes |
|--------|----------|-------|
| **CaseText** | Hybrid keyword + semantic | Strong for case law |
| **Harvey AI** | Fine-tuned legal LLM | Claude-based, expensive |
| **Lexis+ AI** | Massive corpus, traditional IR | Less semantic |
| **vLex Vincent** | European law focus | Graph-based citations |

### 8.4 Key Takeaways for Our Implementation

1. **HyDE is validated** - Multiple papers show 10-20% improvement in retrieval
2. **Iteration limit of 2-3 is standard** - Beyond that, diminishing returns
3. **Graph-based is the frontier** - But requires significant investment
4. **Hybrid approaches win** - No single technique is sufficient
5. **Domain-specific tuning matters** - Generic solutions underperform

---

## 9. Implementation Plan

### 9.1 Phase 1 Timeline (HyDE + Agentic RAG)

```
Week 1:
├── Day 1-2: HyDE Generator component
│   ├── Arabic prompt engineering
│   ├── Multiple hypothetical generation
│   └── Unit tests
├── Day 3-4: Coverage Analyzer component
│   ├── Legal area definitions
│   ├── Keyword matching
│   └── Gap identification
└── Day 5: Cross-Reference Expander
    ├── Regex patterns for Arabic article refs
    └── Direct article fetching

Week 2:
├── Day 1-3: Retrieval Agent orchestration
│   ├── State management
│   ├── Iteration loop
│   └── End condition logic
├── Day 4-5: Evaluation artifacts
│   ├── Schema definition
│   ├── Supabase tables
│   └── Logging integration

Week 3:
├── Day 1-2: Integration with existing agents
│   ├── Update Legal Search Agent
│   ├── Backward compatibility
│   └── Configuration flags
├── Day 3-4: Testing
│   ├── Test case: Hamza Awad
│   ├── Edge cases
│   └── Performance benchmarks
└── Day 5: Documentation & deployment
```

### 9.2 Files to Create/Modify

```
poa_agents/legal_search_agent/project/
├── components/
│   ├── decomposer.py              # Existing (minor updates)
│   ├── retriever.py               # DEPRECATED → retrieval_agent.py
│   ├── synthesizer.py             # Existing (minor updates)
│   ├── hyde_generator.py          # NEW
│   ├── coverage_analyzer.py       # NEW
│   ├── crossref_expander.py       # NEW
│   └── retrieval_agent.py         # NEW - Main orchestrator
├── models/
│   └── retrieval_state.py         # NEW - State dataclasses
├── config/
│   └── legal_areas.yaml           # NEW - Coverage definitions
└── acp.py                         # MODIFIED - Use retrieval_agent
```

### 9.3 Configuration

```yaml
# config/retrieval_config.yaml

hyde:
  enabled: true
  language: "arabic"
  num_hypotheticals: 2
  model: "gpt-4o-mini"
  temperature: 0.7

agentic_loop:
  max_iterations: 3
  iteration_purposes:
    1: "broad_retrieval"
    2: "gap_filling"
    3: "reference_expansion"

end_conditions:
  coverage_threshold: 0.8
  confidence_threshold: 0.55
  min_articles: 5
  max_articles: 30

legal_areas:
  agency_law:
    required: true
    keywords_ar: ["وكالة", "موكل", "وكيل"]
    min_similarity: 0.5
  delegation_limits:
    required: true
    keywords_ar: ["حدود", "تجاوز", "يزيد"]
    min_similarity: 0.5
  # ... more areas

artifacts:
  save_iterations: true
  save_hypotheticals: true
  save_coverage_checks: true
```

---

## 10. Appendix

### A. Arabic Legal Terminology Reference

| English | Arabic | Usage |
|---------|--------|-------|
| Agency | الوكالة | General concept |
| Principal | الموكل | The one who grants |
| Agent | الوكيل | The one who receives |
| Delegation | تفويض | Act of delegating |
| Authority | صلاحية | Power to act |
| Capacity | أهلية | Legal competence |
| Scope | نطاق | Extent of authority |
| Void | باطل | Legally null |
| Commercial Register | السجل التجاري | CR |
| Manager | المدير | Company manager |
| Article | المادة | Legal article |

### B. Regex Patterns for Cross-Reference Detection

```python
CROSS_REFERENCE_PATTERNS = [
    r"المادة\s*\(?\s*(\d+)\s*\)?",        # المادة (5) or المادة 5
    r"المواد\s*\(?\s*(\d+(?:\s*[،,و]\s*\d+)*)\s*\)?",  # المواد (5، 6، 7)
    r"وفقاً للمادة\s*\(?\s*(\d+)\s*\)?",   # وفقاً للمادة (5)
    r"بموجب المادة\s*\(?\s*(\d+)\s*\)?",   # بموجب المادة (5)
    r"انظر المادة\s*\(?\s*(\d+)\s*\)?",    # انظر المادة (5)
    r"طبقاً للمادة\s*\(?\s*(\d+)\s*\)?",   # طبقاً للمادة (5)
    r"المشار إليها في المادة\s*\(?\s*(\d+)\s*\)?",  # المشار إليها في المادة (5)
]
```

### C. Evaluation Metrics Definitions

| Metric | Formula | Target |
|--------|---------|--------|
| **Coverage Score** | (Areas with articles) / (Required areas) | > 0.9 |
| **Avg Similarity** | Mean(article similarities) | > 0.6 |
| **Top-3 Similarity** | Mean(top 3 similarities) | > 0.7 |
| **Reference Coverage** | (Fetched refs) / (Detected refs) | > 0.95 |
| **Iteration Efficiency** | (New articles in iter N) / (Total iter N articles) | > 0.3 |

### D. Cost Estimation

| Component | Calls per Case | Cost per Call | Total |
|-----------|---------------|---------------|-------|
| HyDE Generation | ~6 | $0.001 | $0.006 |
| Coverage Analysis | ~3 | $0.001 | $0.003 |
| Embeddings | ~20 | $0.0001 | $0.002 |
| **Total per Case** | | | **~$0.01** |

At 1000 cases/month: ~$10/month for retrieval (excluding synthesis).

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-13 | Claude + Musa | Initial deep research document |

---

## Next Steps

1. [ ] Review and approve this document
2. [ ] Set up evaluation infrastructure
3. [ ] Implement HyDE generator
4. [ ] Implement coverage analyzer
5. [ ] Implement retrieval agent
6. [ ] Test with Hamza Awad case
7. [ ] Iterate based on results
