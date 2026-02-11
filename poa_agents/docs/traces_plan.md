# Trace Viewer & Commenter — V0 Specification

## Overview

A system to capture, view, and annotate agent execution traces. Enables quality tracking, debugging, and institutional knowledge building around agent runs.

**Goals:**
1. Capture structured traces of agent executions (condenser, legal search)
2. Enable human annotation (comments, tags) on any part of a trace
3. Export/import for offline analysis and backup
4. Provide a queryable history of agent runs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend                                   │
├─────────────────────────────────────────────────────────────────────┤
│  TraceListView    │  TraceDetailView    │  CommentPanel  │  Export  │
│  - Filters        │  - Timeline         │  - Inline      │  - JSON  │
│  - Search         │  - Span tree        │  - Thread      │  - CSV   │
│  - Status chips   │  - Event log        │  - Tags        │  - Batch │
└────────┬──────────┴─────────┬───────────┴───────┬────────┴────┬─────┘
         │                    │                   │             │
         ▼                    ▼                   ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Supabase (PostgreSQL)                            │
├─────────────────────────────────────────────────────────────────────┤
│  traces  │  spans  │  events  │  comments  │  comment_tags         │
└──────────┴─────────┴──────────┴────────────┴───────────────────────┘
         ▲                    ▲
         │                    │
┌────────┴────────────────────┴───────────────────────────────────────┐
│                    Trace Collector                                   │
│  - Wraps agent handlers                                             │
│  - Captures inputs/outputs                                          │
│  - Measures timing                                                  │
│  - Emits structured spans                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Design Principle: UUID PKs for Relations, TEXT IDs for Display

- **Internal relations** use UUID primary/foreign keys for performance and integrity
- **External IDs** (`trace_id`, `span_id`, `event_id`) are TEXT UNIQUE for human-readable display/export
- FKs always reference the UUID `id` column, never the TEXT external ID

### 1. `traces` — Root of each agent invocation

```sql
CREATE TABLE traces (
    -- Primary key (internal)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External ID (for display/export/API)
    trace_id        TEXT UNIQUE NOT NULL,      -- e.g., "tr_20260211_abc123"

    -- Context
    session_id      TEXT,                       -- Groups related traces (e.g., same user session)
    user_id         TEXT,                       -- Hashed user identifier
    application_id  UUID,                       -- FK to applications table (if applicable)

    -- Agent info
    agent_name      TEXT NOT NULL,              -- "condenser", "legal_search"
    agent_version   TEXT,                       -- Semver or commit hash
    environment     TEXT DEFAULT 'production', -- "development", "staging", "production"

    -- Timing
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,
    duration_ms     INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (end_time - start_time)) * 1000
    ) STORED,

    -- Status
    status          TEXT NOT NULL DEFAULT 'running', -- "running", "success", "error", "timeout"
    error_summary   TEXT,                       -- Brief error description if failed

    -- Structure (UUID refs, set after root span created)
    root_span_id    UUID,                       -- Points to the root span (set after insert)
    span_count      INTEGER DEFAULT 0,
    event_count     INTEGER DEFAULT 0,

    -- Flexible metadata
    metadata        JSONB DEFAULT '{}',         -- env vars, headers, feature flags, etc.

    -- Input/Output snapshots (for debugging)
    input_snapshot  JSONB,                      -- Redacted input payload
    output_snapshot JSONB,                      -- Redacted output payload

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_traces_trace_id ON traces(trace_id);          -- For external ID lookups
CREATE INDEX idx_traces_agent_name ON traces(agent_name);
CREATE INDEX idx_traces_start_time ON traces(start_time DESC);
CREATE INDEX idx_traces_status ON traces(status);
CREATE INDEX idx_traces_application_id ON traces(application_id);
CREATE INDEX idx_traces_session_id ON traces(session_id);
```

### 2. `spans` — Units of work within a trace

```sql
CREATE TABLE spans (
    -- Primary key (internal)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External ID (for display/export/API)
    span_id         TEXT UNIQUE NOT NULL,       -- e.g., "sp_abc123_001"

    -- Relations (UUID FKs for integrity + performance)
    trace_db_id     UUID NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES spans(id) ON DELETE CASCADE,  -- NULL for root span

    -- Identity
    name            TEXT NOT NULL,              -- "llm_chat", "semantic_search", "decompose"
    type            TEXT NOT NULL,              -- See Span Types below

    -- Timing
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,
    duration_ms     INTEGER,

    -- Status
    status          TEXT NOT NULL DEFAULT 'running', -- "running", "success", "error"
    error           JSONB,                      -- {code, message, stack_trace}

    -- Flexible attributes (varies by span type)
    attributes      JSONB DEFAULT '{}',

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_spans_span_id ON spans(span_id);              -- For external ID lookups
CREATE INDEX idx_spans_trace_db_id ON spans(trace_db_id);
CREATE INDEX idx_spans_parent_id ON spans(parent_id);
CREATE INDEX idx_spans_type ON spans(type);
CREATE INDEX idx_spans_start_time ON spans(start_time);

-- Add FK from traces.root_span_id after spans table exists
ALTER TABLE traces ADD CONSTRAINT fk_traces_root_span
    FOREIGN KEY (root_span_id) REFERENCES spans(id) ON DELETE SET NULL;
```

**Span Types & Expected Attributes:**

| type | name examples | attributes |
|------|---------------|------------|
| `llm_call` | "gpt-4o_chat", "claude_completion" | `{model, temperature, input_tokens, output_tokens, prompt_hash}` |
| `embedding` | "text-embedding-3-small" | `{model, dimensions, input_count, batch_size}` |
| `retrieval` | "semantic_search", "hybrid_search" | `{query, top_k, threshold, result_count, avg_similarity}` |
| `tool_call` | "decompose", "synthesize" | `{tool_name, input_size, output_size}` |
| `db_query` | "get_legal_brief", "save_opinion" | `{table, operation, row_count}` |
| `http` | "fetch_document", "call_api" | `{method, url, status_code, response_size}` |
| `internal` | "parse_json", "format_output" | `{operation}` |

### 3. `events` — Fine-grained log within spans (optional)

```sql
CREATE TABLE events (
    -- Primary key (internal)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External ID (for display/export/API)
    event_id        TEXT UNIQUE NOT NULL,       -- e.g., "ev_001x9y8_001"

    -- Relations (UUID FKs)
    trace_db_id     UUID NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
    span_db_id      UUID REFERENCES spans(id) ON DELETE CASCADE,  -- NULL if trace-level event

    -- Event details
    timestamp       TIMESTAMPTZ NOT NULL,
    kind            TEXT NOT NULL,              -- See Event Kinds below
    name            TEXT,                       -- Optional descriptive name

    -- Payload (redacted where required)
    payload         JSONB DEFAULT '{}',

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_event_id ON events(event_id);          -- For external ID lookups
CREATE INDEX idx_events_trace_db_id ON events(trace_db_id);
CREATE INDEX idx_events_span_db_id ON events(span_db_id);
CREATE INDEX idx_events_kind ON events(kind);
CREATE INDEX idx_events_timestamp ON events(timestamp);
```

**Event Kinds:**

| kind | description | payload example |
|------|-------------|-----------------|
| `user_msg` | User input message | `{role: "user", content: "...truncated..."}` |
| `assistant_msg` | Assistant response | `{role: "assistant", content: "...truncated..."}` |
| `tool_call` | Tool invocation | `{tool: "decompose", args: {...}}` |
| `tool_result` | Tool response | `{tool: "decompose", result: {...}}` |
| `retrieval_query` | Search query | `{query_text, query_type, language}` |
| `retrieval_result` | Search results | `{article_count, top_similarity, articles: [...]}` |
| `hyde_generation` | HyDE hypothetical | `{hypothetical_text, iteration}` |
| `error` | Error occurred | `{code, message, recoverable}` |
| `metric` | Performance metric | `{name, value, unit}` |
| `annotation` | System annotation | `{message, severity}` |

### 4. `comments` — Human annotations

```sql
CREATE TABLE comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Target (polymorphic reference using UUID FKs)
    trace_db_id     UUID NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
    span_db_id      UUID REFERENCES spans(id) ON DELETE SET NULL,
    event_db_id     UUID REFERENCES events(id) ON DELETE SET NULL,
    target_type     TEXT NOT NULL,              -- "trace", "span", "event"

    -- Content
    author          TEXT NOT NULL,              -- Username or email
    body            TEXT NOT NULL,              -- Markdown supported

    -- Organization
    tags            TEXT[] DEFAULT '{}',        -- ["bug", "quality", "needs-review"]
    rating          INTEGER CHECK (rating >= 1 AND rating <= 5), -- Optional 1-5 rating

    -- Threading
    parent_id       UUID REFERENCES comments(id) ON DELETE CASCADE, -- For replies

    -- Status
    resolved        BOOLEAN DEFAULT FALSE,      -- Mark as resolved
    resolved_by     TEXT,
    resolved_at     TIMESTAMPTZ,

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint: target_type must match which FK is populated
    CONSTRAINT chk_comment_target CHECK (
        (target_type = 'trace' AND span_db_id IS NULL AND event_db_id IS NULL) OR
        (target_type = 'span' AND span_db_id IS NOT NULL AND event_db_id IS NULL) OR
        (target_type = 'event' AND event_db_id IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_comments_trace_db_id ON comments(trace_db_id);
CREATE INDEX idx_comments_span_db_id ON comments(span_db_id);
CREATE INDEX idx_comments_event_db_id ON comments(event_db_id);
CREATE INDEX idx_comments_author ON comments(author);
CREATE INDEX idx_comments_tags ON comments USING GIN(tags);
CREATE INDEX idx_comments_created_at ON comments(created_at DESC);
```

### 5. `comment_tags` — Predefined tag vocabulary (optional)

```sql
CREATE TABLE comment_tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT UNIQUE NOT NULL,       -- "bug", "quality-issue", "hallucination"
    color           TEXT,                       -- "#ff0000"
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed common tags
INSERT INTO comment_tags (name, color, description) VALUES
    ('bug', '#dc2626', 'Agent bug or unexpected behavior'),
    ('quality-issue', '#f59e0b', 'Output quality concern'),
    ('hallucination', '#7c3aed', 'Factual error or fabrication'),
    ('good-example', '#16a34a', 'High quality output worth studying'),
    ('needs-review', '#2563eb', 'Requires expert review'),
    ('scope-violation', '#dc2626', 'POA scope exceeded'),
    ('citation-error', '#f59e0b', 'Wrong or missing legal citation'),
    ('performance', '#6b7280', 'Performance-related observation');
```

---

## ID Generation Strategy

**Trace IDs:**
```
tr_{YYYYMMDD}_{agent}_{random8}
Example: tr_20260211_condenser_a1b2c3d4
```

**Span IDs:**
```
sp_{trace_short}_{sequence}_{random4}
Example: sp_a1b2c3d4_001_x9y8
```

**Event IDs:**
```
ev_{span_short}_{sequence}
Example: ev_001x9y8_001
```

**Rules:**
- IDs are generated at creation time and NEVER modified
- IDs are globally unique (no reuse even across traces)
- IDs are human-readable for debugging
- Include timestamp component for rough ordering

---

## Comment System

### Comment Targets

Comments can be attached to three levels (using UUID FKs internally):

| target_type | trace_db_id | span_db_id | event_db_id | Use case |
|-------------|-------------|------------|-------------|----------|
| `trace` | required | NULL | NULL | Overall run feedback |
| `span` | required | required | NULL | Feedback on specific operation |
| `event` | required | optional | required | Feedback on specific message/action |

The CHECK constraint ensures target_type matches which FK columns are populated.

### Comment Features

1. **Markdown body** — Rich text with code blocks, links
2. **Tags** — Categorization from predefined vocabulary
3. **Rating** — Optional 1-5 quality score
4. **Threading** — Reply to existing comments
5. **Resolution** — Mark issues as resolved

### Comment Workflow

```
1. User views trace detail
2. Clicks "Add Comment" on trace/span/event
3. Writes comment, selects tags, optional rating
4. Comment saved with author + timestamp
5. Other users can reply or resolve
6. Comments visible in trace detail view
7. Comments searchable/filterable in list view
```

---

## Export System

### Export Formats

**JSON (Required):**
```json
{
  "export_meta": {
    "exported_at": "2026-02-11T15:00:00Z",
    "exported_by": "user@example.com",
    "filter": {"agent_name": "legal_search", "date_range": ["2026-02-01", "2026-02-11"]},
    "record_count": 42,
    "version": "1.0"
  },
  "traces": [
    {
      "trace_id": "tr_20260211_legal_search_a1b2c3d4",
      "agent_name": "legal_search",
      "agent_version": "1.2.0",
      "environment": "production",
      "start_time": "2026-02-11T14:30:00Z",
      "end_time": "2026-02-11T14:31:45Z",
      "duration_ms": 105000,
      "status": "success",
      "metadata": {...},
      "spans": [
        {
          "span_id": "sp_a1b2c3d4_001_x9y8",
          "name": "decompose",
          "type": "tool_call",
          "start_time": "...",
          "duration_ms": 5200,
          "attributes": {...},
          "events": [...]
        }
      ],
      "comments": [
        {
          "id": "...",
          "target_type": "trace",
          "author": "reviewer@example.com",
          "body": "Good handling of scope violation case",
          "tags": ["good-example"],
          "rating": 5,
          "created_at": "..."
        }
      ]
    }
  ]
}
```

**CSV (Nice-to-have):**

Flattened format for spreadsheet analysis:
```csv
trace_id,agent_name,start_time,duration_ms,status,comment_count,avg_rating,tags
tr_20260211_...,legal_search,2026-02-11T14:30:00Z,105000,success,2,4.5,"good-example,quality-issue"
```

### Export Scopes

| Scope | Description | Use case |
|-------|-------------|----------|
| Single trace | One trace with all spans, events, comments | Deep dive debugging |
| Batch by filter | All traces matching filter criteria | Quality review session |
| Date range | All traces in time window | Daily/weekly export |

### Export API

```typescript
// Frontend
POST /api/traces/export
{
  "format": "json" | "csv",
  "scope": "single" | "batch" | "date_range",
  "trace_id": "...",              // for single
  "filters": {...},               // for batch
  "start_date": "...",            // for date_range
  "end_date": "...",
  "include_events": true,         // optional, default true
  "include_comments": true        // optional, default true
}

Response: { download_url: "..." } or stream directly
```

### Import (Optional)

Re-ingest exported JSON:
- Preserves original IDs where possible
- Skips duplicates (by trace_id)
- Reports conflicts/skips
- Use case: Restore from backup, migrate between environments

---

## Trace Collection

### Strategy: Automatic Client Instrumentation

Rather than manually wrapping every call site, we instrument the shared clients that all agents use. This captures prompts, tool calls, and results automatically.

**Key insight:** All LLM calls flow through `LLMClient.chat()`, all DB calls flow through `SupabaseClient.*`. Instrument these once, capture everything.

### 1. TraceContext (Thread-Local State)

```python
# shared/tracing/context.py
from contextvars import ContextVar
from typing import Optional
import time
import uuid

_current_trace: ContextVar[Optional["Trace"]] = ContextVar("current_trace", default=None)
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)

def current_trace() -> Optional["Trace"]:
    return _current_trace.get()

def current_span() -> Optional["Span"]:
    return _current_span.get()

class Trace:
    def __init__(self, agent_name: str, **metadata):
        self.id = uuid.uuid4()
        self.trace_id = f"tr_{time.strftime('%Y%m%d')}_{agent_name}_{uuid.uuid4().hex[:8]}"
        self.agent_name = agent_name
        self.metadata = metadata
        self.start_time = time.time()
        self.spans: list[Span] = []
        self.status = "running"

    def __enter__(self):
        _current_trace.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end(status="error" if exc_type else "success")
        _current_trace.set(None)

    def span(self, name: str, type: str) -> "Span":
        return Span(trace=self, name=name, type=type, parent=current_span())

    def end(self, status: str, output: dict = None):
        self.status = status
        self.end_time = time.time()
        self.output_snapshot = _truncate_payload(output) if output else None
        _flush_to_supabase(self)  # Async save
```

### 2. Instrumented LLM Client

```python
# shared/tracing/instrumented_llm.py
from .context import current_trace, current_span

class InstrumentedLLMClient:
    """Wraps any LLM client to automatically capture prompts and responses."""

    def __init__(self, base_client, model_name: str = "gpt-4o"):
        self._client = base_client
        self.model_name = model_name

    async def chat(
        self,
        user_message: str,
        system_message: str = "",
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        trace = current_trace()
        parent = current_span()

        # Create span for this LLM call
        span = Span(
            trace=trace,
            name=f"llm_{self.model_name}",
            type="llm_call",
            parent=parent
        )

        with span:
            # Record input (truncated for storage)
            span.event("prompt", {
                "system": system_message[:2000],
                "user": user_message[:5000],
                "model": self.model_name,
                "temperature": temperature,
            })

            # Make the actual call
            start = time.time()
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                **kwargs
            )

            # Record output
            content = response.choices[0].message.content
            span.set_attributes({
                "duration_ms": int((time.time() - start) * 1000),
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "finish_reason": response.choices[0].finish_reason,
            })
            span.event("response", {
                "content": content[:5000],
                "truncated": len(content) > 5000,
            })

            return content
```

### 3. Instrumented Supabase Client

```python
# shared/tracing/instrumented_supabase.py
from .context import current_trace, current_span

class InstrumentedSupabaseClient:
    """Wraps Supabase client to capture queries and results."""

    def __init__(self, base_client):
        self._client = base_client

    def semantic_search(
        self,
        query_embedding: list[float],
        language: str = "arabic",
        limit: int = 10,
        threshold: float = 0.3,
    ) -> list[dict]:
        trace = current_trace()

        span = Span(
            trace=trace,
            name="semantic_search",
            type="retrieval",
            parent=current_span()
        )

        with span:
            span.event("retrieval_query", {
                "language": language,
                "limit": limit,
                "threshold": threshold,
                "embedding_dim": len(query_embedding),
            })

            start = time.time()
            results = self._client.rpc(
                "match_poa_articles",
                {"query_embedding": query_embedding, ...}
            ).execute()

            span.set_attributes({
                "duration_ms": int((time.time() - start) * 1000),
                "result_count": len(results.data),
                "top_similarity": results.data[0]["similarity"] if results.data else 0,
                "avg_similarity": sum(r["similarity"] for r in results.data) / len(results.data) if results.data else 0,
            })
            span.event("retrieval_result", {
                "articles": [
                    {"article_number": r["article_number"], "similarity": r["similarity"]}
                    for r in results.data[:10]
                ],
            })

            return results.data
```

### 4. Instrumented Embedding Client

```python
# shared/tracing/instrumented_embeddings.py
class InstrumentedEmbeddingClient:
    """Wraps embedding client to capture input/output."""

    async def embed(self, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        span = Span(
            trace=current_trace(),
            name=f"embed_{model}",
            type="embedding",
            parent=current_span()
        )

        with span:
            span.event("embed_input", {
                "text_count": len(texts),
                "total_chars": sum(len(t) for t in texts),
                "sample": texts[0][:500] if texts else "",
            })

            start = time.time()
            response = await self._client.embeddings.create(input=texts, model=model)

            span.set_attributes({
                "duration_ms": int((time.time() - start) * 1000),
                "model": model,
                "dimensions": len(response.data[0].embedding),
                "total_tokens": response.usage.total_tokens,
            })

            return [d.embedding for d in response.data]
```

### 5. Agent Handler Integration

```python
# In condenser_agent/project/acp.py
from shared.tracing import Trace, InstrumentedLLMClient

@acp.on_message_send
async def handle_message_send(params):
    # Start trace at handler entry
    with Trace(agent_name="condenser", application_id=application_id) as trace:
        trace.event("input", {"payload_size": len(user_message)})

        # Use instrumented client - all calls auto-traced
        llm = InstrumentedLLMClient(get_raw_llm_client())

        # ... rest of handler ...
        # Every llm.chat() call automatically creates spans with prompts/responses

        response = await llm.chat(user_message=prompt, system_message=system_prompt)

        trace.set_output(legal_brief)
    # Trace auto-saved on context exit
```

```python
# In legal_search_agent/project/acp.py
from shared.tracing import Trace, InstrumentedLLMClient, InstrumentedSupabaseClient

@acp.on_message_send
async def handle_message_send(params):
    with Trace(agent_name="legal_search", application_id=application_id) as trace:
        # Wrap clients - all nested calls auto-traced
        llm = InstrumentedLLMClient(get_raw_llm_client())
        supabase = InstrumentedSupabaseClient(get_raw_supabase_client())
        embeddings = InstrumentedEmbeddingClient(get_raw_embedding_client())

        # Pass instrumented clients to components
        decomposer = Decomposer(llm)
        retrieval_agent = RetrievalAgent(llm, supabase, embeddings)
        synthesizer = Synthesizer(llm)

        # All calls now auto-traced with full prompt/response capture
        with trace.span("decompose", type="tool_call"):
            issues = await decomposer.decompose(legal_brief, locale)

        with trace.span("retrieval", type="retrieval"):
            articles = await retrieval_agent.retrieve(issues)

        with trace.span("synthesize", type="tool_call"):
            opinion = await synthesizer.synthesize(...)
```

### What Gets Captured Automatically

| Component | Captured Data |
|-----------|---------------|
| LLM calls | system_prompt, user_prompt, response, tokens, latency, model |
| Embeddings | input texts, dimensions, tokens, latency |
| Semantic search | query params, result count, similarities, top articles |
| HyDE generation | hypothetical texts generated, iteration number |
| Tool calls | input args, output, duration |

### Payload Truncation Rules

To avoid bloating storage:
- Prompts: max 5000 chars (store hash of full if truncated)
- Responses: max 5000 chars
- Embeddings: don't store vectors, just metadata
- Search results: store top 10 article numbers + similarities

---

## Frontend Components

### 1. TraceListPage (`/traces`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Traces                                              [Export ▼]     │
├─────────────────────────────────────────────────────────────────────┤
│  Filters: [Agent ▼] [Status ▼] [Date Range    ] [Has Comments ☐]   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ✓ tr_20260211_legal_search_a1b2c3d4                         │   │
│  │   legal_search • 1m 45s • 2 hours ago                       │   │
│  │   [success] [2 comments] [★★★★☆]                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ✗ tr_20260211_condenser_b2c3d4e5                            │   │
│  │   condenser • 32s • 3 hours ago                             │   │
│  │   [error: timeout] [1 comment] [bug]                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ...                                                               │
├─────────────────────────────────────────────────────────────────────┤
│  Showing 1-20 of 156 traces                    [← Prev] [Next →]   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. TraceDetailPage (`/traces/:trace_id`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Back to Traces                                                   │
│                                                                     │
│  tr_20260211_legal_search_a1b2c3d4                    [Export JSON] │
│  legal_search v1.2.0 • production • 1m 45s                         │
│  Started: Feb 11, 2026 2:30 PM                                     │
├─────────────────────────────────────────────────────────────────────┤
│  [Timeline] [Spans] [Events] [Comments (3)] [Raw JSON]             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Timeline                                                           │
│  ────────────────────────────────────────────────────────────────  │
│  0s        30s        60s        90s       105s                    │
│  │          │          │          │          │                      │
│  ├─ decompose (5.2s) ─┤                                            │
│  │  └─ llm_call ──────┤                                            │
│  │                                                                  │
│  ├──────────── retrieval (85s) ─────────────────────────┤          │
│  │  ├─ iteration_0 (28s) ─┤                                        │
│  │  │  ├─ hyde (8s) ─┤                                             │
│  │  │  ├─ embed (2s) ┤                                             │
│  │  │  └─ search (18s) ──┤                                         │
│  │  ├─ iteration_1 (32s) ─────┤                                    │
│  │  └─ iteration_2 (25s) ────┤                                     │
│  │                                                                  │
│  └───────────────── synthesize (15s) ───────────────────┤          │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  💬 Comments                                         [+ Add Comment] │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ reviewer@example.com • 1 hour ago         [good-example] ★★★★★ │
│  │ Excellent handling of the scope violation. The HyDE           │
│  │ hypotheticals were well-targeted.                             │
│  │                                              [Reply] [Resolve] │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. CommentModal

```
┌─────────────────────────────────────────────────────────────────────┐
│  Add Comment                                                    [×] │
├─────────────────────────────────────────────────────────────────────┤
│  Target: span "retrieval > iteration_1 > hyde"                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ The hypothetical here drifted off-topic. It generated       │   │
│  │ text about property law when the issue was about POA scope. │   │
│  │                                                             │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Tags: [hallucination ×] [quality-issue ×] [+ Add tag]             │
│                                                                     │
│  Rating: ☆ ☆ ★ ☆ ☆  (2/5)                                          │
│                                                                     │
│                                    [Cancel]  [Save Comment]        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Traces

```
GET    /api/traces                    List traces (with filters)
GET    /api/traces/:trace_id          Get trace detail with spans/events
POST   /api/traces/export             Export traces

Query params for list:
  - agent_name: string
  - status: string
  - start_date, end_date: ISO dates
  - has_comments: boolean
  - min_rating: number
  - tags: string[] (any match)
  - limit, offset: pagination
```

### Comments

```
GET    /api/traces/:trace_id/comments       List comments for trace
POST   /api/traces/:trace_id/comments       Create comment
PATCH  /api/comments/:comment_id            Update comment
DELETE /api/comments/:comment_id            Delete comment
POST   /api/comments/:comment_id/resolve    Resolve comment
```

---

## Implementation Phases

### Phase 1: Database Schema

**1.1 Create Supabase migrations**
- [ ] Create `traces` table with all columns and indexes
- [ ] Create `spans` table with FK to traces + self-referential parent_id
- [ ] Create `events` table with FKs to traces and spans
- [ ] Create `comments` table with polymorphic target FKs + CHECK constraint
- [ ] Create `comment_tags` table and seed default tags
- [ ] Add FK constraint from `traces.root_span_id` → `spans.id`
- [ ] Test all constraints (CASCADE deletes, CHECK constraint validation)

**1.2 Create DB helper functions**
- [ ] Create RPC function `get_trace_with_children(trace_id UUID)` — returns trace + all spans + all events in one call
- [ ] Create RPC function `get_trace_comments(trace_id UUID)` — returns all comments with replies threaded
- [ ] Add Row Level Security policies (if multi-tenancy needed)

---

### Phase 2: Python Tracing Library

**2.1 Core tracing infrastructure**
- [ ] Create `shared/tracing/` directory structure
- [ ] Implement `context.py` with `ContextVar` for `_current_trace` and `_current_span`
- [ ] Implement `Trace` class with `__enter__`/`__exit__`, span creation, and auto-flush
- [ ] Implement `Span` class with timing, attributes, events, and status tracking
- [ ] Implement `Event` class for fine-grained logging within spans
- [ ] Implement ID generation functions (`generate_trace_id`, `generate_span_id`, `generate_event_id`)

**2.2 Database persistence**
- [ ] Implement `_flush_to_supabase(trace)` — async batch insert of trace + spans + events
- [ ] Add payload truncation helper (`_truncate_payload`) with configurable limits
- [ ] Add error handling for DB write failures (log but don't crash agent)
- [ ] Implement background flush queue to avoid blocking agent response

**2.3 Instrumented clients**
- [ ] Implement `InstrumentedLLMClient` wrapping OpenAI client
  - [ ] Capture system_prompt, user_prompt (truncated)
  - [ ] Capture response content (truncated)
  - [ ] Capture token counts, latency, model, temperature
- [ ] Implement `InstrumentedSupabaseClient` wrapping Supabase client
  - [ ] Capture semantic search calls with query params + results
  - [ ] Capture RPC calls with function name + args + result count
- [ ] Implement `InstrumentedEmbeddingClient` wrapping embedding API
  - [ ] Capture input text count, total chars, sample
  - [ ] Capture dimensions, tokens, latency

**2.4 Integrate into condenser_agent**
- [ ] Import tracing in `condenser_agent/project/acp.py`
- [ ] Wrap handler in `with Trace(agent_name="condenser", ...)`
- [ ] Replace raw LLM client with `InstrumentedLLMClient`
- [ ] Add manual spans for major steps (context loading, analysis, output formatting)
- [ ] Test: verify traces appear in DB after agent run

**2.5 Integrate into legal_search_agent**
- [ ] Import tracing in `legal_search_agent/project/acp.py`
- [ ] Wrap handler in `with Trace(agent_name="legal_search", ...)`
- [ ] Replace clients in decomposer, HyDE generator, retrieval agent, coverage analyzer, synthesizer
- [ ] Add spans for each pipeline stage (decompose, retrieval iterations, synthesize)
- [ ] Test: verify full trace tree in DB after agent run

---

### Phase 3: Frontend - Trace List View

**3.1 Create traces page structure**
- [ ] Create `/traces` page route (`src/app/traces/page.tsx`)
- [ ] Create `TraceListView` component
- [ ] Create Supabase query hook `useTraces({ filters, pagination })`
- [ ] Add navigation link to traces page in main layout

**3.2 Implement filters**
- [ ] Agent name dropdown filter (condenser, legal_search)
- [ ] Status filter (success, error, running, timeout)
- [ ] Date range picker
- [ ] "Has comments" checkbox
- [ ] "Min rating" slider
- [ ] Tags multi-select
- [ ] Wire filters to query params + Supabase query

**3.3 Implement trace list**
- [ ] `TraceCard` component showing: trace_id, agent, duration, status, comment count, avg rating, tags
- [ ] Status chips with color coding
- [ ] Relative time display ("2 hours ago")
- [ ] Click to navigate to detail page
- [ ] Pagination controls (limit/offset)

---

### Phase 4: Frontend - Trace Detail View

**4.1 Create detail page structure**
- [ ] Create `/traces/[traceId]` page route (`src/app/traces/[traceId]/page.tsx`)
- [ ] Create Supabase query hook `useTraceDetail(traceId)` — fetches trace + spans + events
- [ ] Create header showing trace metadata (id, agent, version, env, timing, status)
- [ ] Add "Export JSON" button in header

**4.2 Implement timeline visualization**
- [ ] Calculate relative start times for all spans
- [ ] Render horizontal bars proportional to duration
- [ ] Nest child spans under parents (indentation)
- [ ] Color code by span type (llm_call, retrieval, tool_call, etc.)
- [ ] Hover tooltip showing span name, duration, status
- [ ] Click span to select and show details

**4.3 Implement span detail panel**
- [ ] Side panel showing selected span details
- [ ] Display all attributes in key-value format
- [ ] List events within span chronologically
- [ ] Expand/collapse for long payloads
- [ ] JSON viewer for raw attributes
- [ ] "Add Comment" button for selected span

**4.4 Implement events log view**
- [ ] Chronological list of all events in trace
- [ ] Filter by event kind (user_msg, assistant_msg, tool_call, etc.)
- [ ] Expand/collapse event payloads
- [ ] Click event to highlight parent span in timeline
- [ ] "Add Comment" button for events

**4.5 Implement tabs**
- [ ] Tab navigation: Timeline | Spans | Events | Comments | Raw JSON
- [ ] Spans tab: flat list of all spans with search/filter
- [ ] Raw JSON tab: full trace export preview
- [ ] Comments tab count shows total comments

---

### Phase 5: Comment System

**5.1 Comment data layer**
- [ ] Create Supabase query hook `useComments(traceId)`
- [ ] Create mutation hook `useCreateComment()`
- [ ] Create mutation hook `useUpdateComment()`
- [ ] Create mutation hook `useResolveComment()`
- [ ] Create mutation hook `useDeleteComment()`

**5.2 Comment display**
- [ ] `CommentCard` component showing: author, timestamp, body, tags, rating
- [ ] Markdown rendering for comment body
- [ ] Tag chips with colors from `comment_tags` table
- [ ] Star rating display
- [ ] Reply button
- [ ] Resolve button (shows resolved status)
- [ ] Edit/Delete buttons (for own comments)

**5.3 Comment panel in trace detail**
- [ ] `CommentsPanel` component listing all comments
- [ ] Group by target (trace-level, then by span/event)
- [ ] Indicate comment target with breadcrumb ("span: decompose > llm_call")
- [ ] Thread replies under parent comments
- [ ] "Add Comment" button at top

**5.4 Comment creation modal**
- [ ] `CommentModal` component
- [ ] Textarea with markdown preview
- [ ] Tag selector (multi-select from predefined tags)
- [ ] Rating input (1-5 stars, optional)
- [ ] Show target context (what span/event being commented on)
- [ ] Save and cancel buttons
- [ ] Validation (body required)

**5.5 Inline comment triggers**
- [ ] "Add Comment" icon on trace header → opens modal with target_type="trace"
- [ ] "Add Comment" icon on span row → opens modal with target_type="span"
- [ ] "Add Comment" icon on event row → opens modal with target_type="event"
- [ ] Comment count badges on spans/events that have comments

---

### Phase 6: Export System

**6.1 JSON export**
- [ ] Create `/api/traces/export` API route
- [ ] Implement single trace export (trace + all spans + events + comments)
- [ ] Implement batch export with filters
- [ ] Implement date range export
- [ ] Add `export_meta` with timestamp, filter, count, version
- [ ] Stream large exports to avoid memory issues

**6.2 Frontend export UI**
- [ ] Export button on trace detail page → downloads single trace JSON
- [ ] Export dropdown on trace list page with options:
  - [ ] "Export current view" (applies current filters)
  - [ ] "Export date range" (opens date picker)
- [ ] Progress indicator for large exports
- [ ] Download via blob URL

**6.3 CSV export (optional)**
- [ ] Flatten trace data to rows (one row per trace)
- [ ] Include summary columns: trace_id, agent, start_time, duration, status, comment_count, avg_rating, tags
- [ ] Option to include spans as separate CSV or as JSON column

---

### Phase 7: Polish & Testing

**7.1 Error handling**
- [ ] Handle DB query failures gracefully in UI
- [ ] Loading skeletons for trace list and detail
- [ ] Empty states (no traces, no comments)
- [ ] Error boundaries for component crashes

**7.2 Performance**
- [ ] Add indexes for common query patterns
- [ ] Lazy load events (fetch only when Events tab selected)
- [ ] Virtual scroll for long span/event lists
- [ ] Debounce filter inputs

**7.3 Testing**
- [ ] Test trace collection in dev environment
- [ ] Verify all span types captured correctly
- [ ] Test comment CRUD operations
- [ ] Test export/import round-trip
- [ ] Test edge cases: very long traces, traces with errors, traces with many comments

**7.4 Documentation**
- [ ] Add tracing setup instructions to agent README
- [ ] Document payload truncation rules
- [ ] Document comment tag vocabulary
- [ ] Add troubleshooting guide for common issues

---

## Open Questions

1. **Retention policy** — How long to keep traces? 30 days? 90 days? Forever?
2. **PII handling** — What fields need redaction in payloads?
3. **Multi-tenancy** — Do we need RLS for different users/teams?
4. **Real-time updates** — Should trace list auto-refresh? WebSocket?
5. **Alerting** — Notify on certain error patterns?
6. **Integration** — Export to external observability tools (Datadog, etc.)?

---

## References

- [OpenTelemetry Tracing Concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
- [Langfuse](https://langfuse.com/) — LLM observability platform
- [Arize Phoenix](https://phoenix.arize.com/) — ML observability
- [Weights & Biases Prompts](https://wandb.ai/site/prompts) — LLM tracing
