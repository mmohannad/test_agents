-- Supabase Migration: Create Tracing Tables
-- Run this in the SQL Editor panel
--
-- Creates tables for agent execution tracing and commenting:
--   - traces: Root of each agent invocation
--   - spans: Units of work within a trace
--   - events: Fine-grained logs within spans
--   - comments: Human annotations on traces/spans/events
--   - comment_tags: Predefined tag vocabulary

--------------------------------------------------------------------------------
-- 1. TRACES TABLE
--------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS traces (
    -- Primary key (internal)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External ID (for display/export/API)
    trace_id        TEXT UNIQUE NOT NULL,      -- e.g., "tr_20260211_condenser_abc123"

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
        CASE
            WHEN end_time IS NOT NULL
            THEN EXTRACT(EPOCH FROM (end_time - start_time)) * 1000
            ELSE NULL
        END
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

-- Indexes for traces
CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_agent_name ON traces(agent_name);
CREATE INDEX IF NOT EXISTS idx_traces_start_time ON traces(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status);
CREATE INDEX IF NOT EXISTS idx_traces_application_id ON traces(application_id);
CREATE INDEX IF NOT EXISTS idx_traces_session_id ON traces(session_id);

-- Comments
COMMENT ON TABLE traces IS 'Root of each agent invocation trace';
COMMENT ON COLUMN traces.trace_id IS 'Human-readable external ID: tr_{YYYYMMDD}_{agent}_{random8}';
COMMENT ON COLUMN traces.duration_ms IS 'Auto-calculated from end_time - start_time';

--------------------------------------------------------------------------------
-- 2. SPANS TABLE
--------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS spans (
    -- Primary key (internal)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External ID (for display/export/API)
    span_id         TEXT UNIQUE NOT NULL,       -- e.g., "sp_abc123_001_x9y8"

    -- Relations (UUID FKs for integrity + performance)
    trace_db_id     UUID NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES spans(id) ON DELETE CASCADE,  -- NULL for root span

    -- Identity
    name            TEXT NOT NULL,              -- "llm_chat", "semantic_search", "decompose"
    type            TEXT NOT NULL,              -- "llm_call", "embedding", "retrieval", "tool_call", "db_query", "http", "internal"

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

-- Indexes for spans
CREATE INDEX IF NOT EXISTS idx_spans_span_id ON spans(span_id);
CREATE INDEX IF NOT EXISTS idx_spans_trace_db_id ON spans(trace_db_id);
CREATE INDEX IF NOT EXISTS idx_spans_parent_id ON spans(parent_id);
CREATE INDEX IF NOT EXISTS idx_spans_type ON spans(type);
CREATE INDEX IF NOT EXISTS idx_spans_start_time ON spans(start_time);

-- Comments
COMMENT ON TABLE spans IS 'Units of work within a trace - forms a tree via parent_id';
COMMENT ON COLUMN spans.type IS 'Span type: llm_call, embedding, retrieval, tool_call, db_query, http, internal';
COMMENT ON COLUMN spans.attributes IS 'Type-specific attributes: tokens for LLM, result_count for retrieval, etc.';

--------------------------------------------------------------------------------
-- 3. EVENTS TABLE
--------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS events (
    -- Primary key (internal)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External ID (for display/export/API)
    event_id        TEXT UNIQUE NOT NULL,       -- e.g., "ev_001x9y8_001"

    -- Relations (UUID FKs)
    trace_db_id     UUID NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
    span_db_id      UUID REFERENCES spans(id) ON DELETE CASCADE,  -- NULL if trace-level event

    -- Event details
    timestamp       TIMESTAMPTZ NOT NULL,
    kind            TEXT NOT NULL,              -- "user_msg", "assistant_msg", "tool_call", "tool_result", etc.
    name            TEXT,                       -- Optional descriptive name

    -- Payload (redacted where required)
    payload         JSONB DEFAULT '{}',

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for events
CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);
CREATE INDEX IF NOT EXISTS idx_events_trace_db_id ON events(trace_db_id);
CREATE INDEX IF NOT EXISTS idx_events_span_db_id ON events(span_db_id);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

-- Comments
COMMENT ON TABLE events IS 'Fine-grained log entries within spans';
COMMENT ON COLUMN events.kind IS 'Event kind: user_msg, assistant_msg, tool_call, tool_result, retrieval_query, retrieval_result, hyde_generation, error, metric, annotation';

--------------------------------------------------------------------------------
-- 4. COMMENT_TAGS TABLE (must be created before comments for FK reference)
--------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS comment_tags (
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
    ('performance', '#6b7280', 'Performance-related observation')
ON CONFLICT (name) DO NOTHING;

COMMENT ON TABLE comment_tags IS 'Predefined vocabulary of tags for categorizing comments';

--------------------------------------------------------------------------------
-- 5. COMMENTS TABLE
--------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS comments (
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

-- Indexes for comments
CREATE INDEX IF NOT EXISTS idx_comments_trace_db_id ON comments(trace_db_id);
CREATE INDEX IF NOT EXISTS idx_comments_span_db_id ON comments(span_db_id);
CREATE INDEX IF NOT EXISTS idx_comments_event_db_id ON comments(event_db_id);
CREATE INDEX IF NOT EXISTS idx_comments_author ON comments(author);
CREATE INDEX IF NOT EXISTS idx_comments_tags ON comments USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at DESC);

-- Comments
COMMENT ON TABLE comments IS 'Human annotations on traces, spans, or events';
COMMENT ON COLUMN comments.target_type IS 'What this comment is attached to: trace, span, or event';
COMMENT ON COLUMN comments.tags IS 'Array of tag names from comment_tags vocabulary';

--------------------------------------------------------------------------------
-- 6. ADD FK FROM traces.root_span_id TO spans.id
--------------------------------------------------------------------------------

ALTER TABLE traces
    ADD CONSTRAINT fk_traces_root_span
    FOREIGN KEY (root_span_id) REFERENCES spans(id) ON DELETE SET NULL;

--------------------------------------------------------------------------------
-- 7. RPC FUNCTION: get_trace_with_children
-- Returns a trace with all its spans and events in one call
--------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_trace_with_children(p_trace_id TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_trace_uuid UUID;
    v_result JSONB;
BEGIN
    -- Get the internal UUID for the trace
    SELECT id INTO v_trace_uuid
    FROM traces
    WHERE trace_id = p_trace_id;

    IF v_trace_uuid IS NULL THEN
        RETURN jsonb_build_object('error', 'Trace not found');
    END IF;

    -- Build the result with trace, spans, and events
    SELECT jsonb_build_object(
        'trace', to_jsonb(t.*),
        'spans', COALESCE(
            (SELECT jsonb_agg(to_jsonb(s.*) ORDER BY s.start_time)
             FROM spans s
             WHERE s.trace_db_id = v_trace_uuid),
            '[]'::jsonb
        ),
        'events', COALESCE(
            (SELECT jsonb_agg(to_jsonb(e.*) ORDER BY e.timestamp)
             FROM events e
             WHERE e.trace_db_id = v_trace_uuid),
            '[]'::jsonb
        )
    ) INTO v_result
    FROM traces t
    WHERE t.id = v_trace_uuid;

    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_trace_with_children IS 'Fetch a trace with all spans and events in one call';

--------------------------------------------------------------------------------
-- 8. RPC FUNCTION: get_trace_comments
-- Returns all comments for a trace with replies threaded
--------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_trace_comments(p_trace_id TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_trace_uuid UUID;
    v_result JSONB;
BEGIN
    -- Get the internal UUID for the trace
    SELECT id INTO v_trace_uuid
    FROM traces
    WHERE trace_id = p_trace_id;

    IF v_trace_uuid IS NULL THEN
        RETURN jsonb_build_object('error', 'Trace not found');
    END IF;

    -- Fetch all comments with span/event external IDs for context
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'id', c.id,
                'target_type', c.target_type,
                'trace_id', p_trace_id,
                'span_id', s.span_id,
                'event_id', e.event_id,
                'author', c.author,
                'body', c.body,
                'tags', c.tags,
                'rating', c.rating,
                'parent_id', c.parent_id,
                'resolved', c.resolved,
                'resolved_by', c.resolved_by,
                'resolved_at', c.resolved_at,
                'created_at', c.created_at,
                'updated_at', c.updated_at
            )
            ORDER BY c.created_at
        ),
        '[]'::jsonb
    ) INTO v_result
    FROM comments c
    LEFT JOIN spans s ON c.span_db_id = s.id
    LEFT JOIN events e ON c.event_db_id = e.id
    WHERE c.trace_db_id = v_trace_uuid;

    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_trace_comments IS 'Fetch all comments for a trace with external IDs';

--------------------------------------------------------------------------------
-- 9. TRIGGER: Auto-update updated_at timestamp
--------------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to traces
DROP TRIGGER IF EXISTS traces_updated_at ON traces;
CREATE TRIGGER traces_updated_at
    BEFORE UPDATE ON traces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to comments
DROP TRIGGER IF EXISTS comments_updated_at ON comments;
CREATE TRIGGER comments_updated_at
    BEFORE UPDATE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

--------------------------------------------------------------------------------
-- DONE
--------------------------------------------------------------------------------
