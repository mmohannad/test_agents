-- ============================================================================
-- SAK AI Agent - Retrieval Evaluation Artifacts Migration v1.0
-- ============================================================================
-- This migration creates the table for storing agentic RAG evaluation artifacts
-- Run this in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: CREATE ENUMS FOR RETRIEVAL
-- ============================================================================

CREATE TYPE retrieval_stop_reason AS ENUM (
    'coverage_threshold_met',
    'confidence_threshold_met',
    'max_iterations_reached',
    'max_articles_reached',
    'max_latency_reached',
    'diminishing_returns',
    'agent_assessment'
);

CREATE TYPE iteration_purpose AS ENUM (
    'broad_retrieval',
    'gap_filling',
    'reference_expansion'
);

-- ============================================================================
-- STEP 2: CREATE RETRIEVAL EVAL ARTIFACTS TABLE
-- ============================================================================

CREATE TABLE retrieval_eval_artifacts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id             VARCHAR(100) UNIQUE NOT NULL,
    application_id          UUID REFERENCES applications(id),

    -- Input Context
    legal_brief             JSONB NOT NULL,
    decomposed_issues       JSONB NOT NULL,

    -- Configuration Used
    config                  JSONB NOT NULL,

    -- Iteration Details (full trace)
    iterations              JSONB NOT NULL,

    -- Final Results
    final_articles          JSONB NOT NULL,
    final_coverage          JSONB NOT NULL,

    -- Stop Reason
    stop_reason             retrieval_stop_reason NOT NULL,
    stop_iteration          INTEGER NOT NULL,

    -- Metrics
    total_iterations        INTEGER NOT NULL,
    total_articles          INTEGER NOT NULL,
    total_llm_calls         INTEGER NOT NULL,
    total_embedding_calls   INTEGER NOT NULL,
    total_latency_ms        INTEGER NOT NULL,

    -- Quality Scores
    avg_similarity          DECIMAL(4,3),
    top_3_similarity        DECIMAL(4,3),
    coverage_score          DECIMAL(4,3),

    -- Cost Tracking
    estimated_cost_usd      DECIMAL(10,6),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for analysis queries
CREATE INDEX idx_retrieval_artifacts_application ON retrieval_eval_artifacts(application_id);
CREATE INDEX idx_retrieval_artifacts_stop_reason ON retrieval_eval_artifacts(stop_reason);
CREATE INDEX idx_retrieval_artifacts_coverage ON retrieval_eval_artifacts(coverage_score);
CREATE INDEX idx_retrieval_artifacts_created ON retrieval_eval_artifacts(created_at);

-- ============================================================================
-- STEP 3: ADD COMMENTS
-- ============================================================================

COMMENT ON TABLE retrieval_eval_artifacts IS 'Stores full traces of agentic RAG retrieval runs for evaluation and debugging. Includes HyDE hypotheticals, iteration logs, coverage analysis, and final results.';
COMMENT ON COLUMN retrieval_eval_artifacts.iterations IS 'Array of iteration logs with queries, hypotheticals, articles found, coverage changes per iteration';
COMMENT ON COLUMN retrieval_eval_artifacts.final_coverage IS 'Coverage status per legal area (agency_law, delegation_limits, etc.)';
COMMENT ON COLUMN retrieval_eval_artifacts.stop_reason IS 'Why the agentic loop terminated (coverage met, max iterations, etc.)';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
