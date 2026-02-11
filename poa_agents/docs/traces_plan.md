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

### Integration Points

**1. Condenser Agent:**
```python
# In acp.py handle_message_send
async def handle_message_send(params):
    trace = TraceCollector.start_trace(
        agent_name="condenser",
        application_id=application_id
    )

    with trace.span("parse_input", type="internal"):
        input_data = json.loads(user_message)

    with trace.span("llm_analysis", type="llm_call") as span:
        response = await llm.chat(prompt, system_message)
        span.set_attributes({
            "model": "gpt-4o",
            "input_tokens": response.usage.input,
            "output_tokens": response.usage.output
        })

    trace.end(status="success", output=legal_brief)
```

**2. Legal Search Agent:**
```python
# In acp.py handle_message_send
async def handle_message_send(params):
    trace = TraceCollector.start_trace(
        agent_name="legal_search",
        application_id=application_id
    )

    with trace.span("decompose", type="tool_call"):
        issues = await decomposer.decompose(legal_brief, locale)

    with trace.span("retrieval", type="retrieval") as retrieval_span:
        for iteration in range(max_iterations):
            with retrieval_span.child(f"iteration_{iteration}") as iter_span:
                # HyDE generation
                with iter_span.child("hyde", type="llm_call"):
                    hypotheticals = await hyde.generate(...)

                # Embedding
                with iter_span.child("embed", type="embedding"):
                    vectors = await embed(hypotheticals)

                # Search
                with iter_span.child("search", type="retrieval"):
                    results = await supabase.semantic_search(vectors)

    with trace.span("synthesize", type="tool_call"):
        opinion = await synthesizer.synthesize(...)

    trace.end(status="success", output=opinion)
```

### TraceCollector API

```python
class TraceCollector:
    @classmethod
    def start_trace(cls, agent_name: str, **metadata) -> Trace:
        """Start a new trace, returns context manager."""

    def span(self, name: str, type: str) -> Span:
        """Create a child span of the current span."""

    def event(self, kind: str, payload: dict):
        """Log an event in the current span."""

    def end(self, status: str, output: dict = None):
        """End the trace and flush to storage."""

class Span:
    def set_attributes(self, attrs: dict):
        """Set span attributes."""

    def child(self, name: str, **kwargs) -> Span:
        """Create a child span."""

    def event(self, kind: str, payload: dict):
        """Log an event in this span."""
```

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

### Phase 1: Data Model & Collection (Week 1)
- [ ] Create Supabase migrations for all tables
- [ ] Implement TraceCollector Python class
- [ ] Instrument condenser_agent with basic tracing
- [ ] Instrument legal_search_agent with full tracing
- [ ] Verify traces are being saved

### Phase 2: Trace Viewer UI (Week 2)
- [ ] TraceListPage with filters and pagination
- [ ] TraceDetailPage with timeline visualization
- [ ] Span detail panel
- [ ] Event log view
- [ ] Connect to Supabase queries

### Phase 3: Comment System (Week 3)
- [ ] Comment data model and API
- [ ] CommentPanel component
- [ ] Inline comment placement (trace/span/event)
- [ ] Tag selector with predefined vocabulary
- [ ] Rating input
- [ ] Comment threading (replies)

### Phase 4: Export & Polish (Week 4)
- [ ] JSON export implementation
- [ ] CSV export (flattened)
- [ ] Export by filter/date range
- [ ] Import functionality (optional)
- [ ] UI polish and testing

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
