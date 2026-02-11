"""
Persistence layer for flushing traces to Supabase.

Handles batched inserts with error handling to avoid
blocking or crashing the main agent flow.
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Trace


# Module-level flag to enable/disable tracing persistence
_tracing_enabled: bool = True


def is_tracing_enabled() -> bool:
    """Check if tracing persistence is enabled."""
    # Check environment variable override
    env_val = os.getenv("TRACING_ENABLED", "true").lower()
    return _tracing_enabled and env_val in ("true", "1", "yes")


def set_tracing_enabled(enabled: bool) -> None:
    """Enable or disable tracing persistence."""
    global _tracing_enabled
    _tracing_enabled = enabled


async def flush_trace(trace: "Trace") -> bool:
    """
    Flush a completed trace to Supabase.

    Inserts the trace, all spans, and all events in batched operations.
    Errors are logged but don't propagate to avoid crashing the agent.

    Args:
        trace: The completed Trace object

    Returns:
        True if flush succeeded, False otherwise
    """
    if not is_tracing_enabled():
        return True  # Silently skip if disabled

    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            print("[tracing] SUPABASE_URL/SUPABASE_ANON_KEY not set, skipping flush")
            return False

        client = create_client(supabase_url, supabase_key)

        # 1. Insert trace
        trace_data = trace.to_dict()
        # Remove generated fields that DB computes
        trace_data.pop("duration_ms", None)

        trace_result = client.table("traces").insert(trace_data).execute()
        if not trace_result.data:
            print(f"[tracing] Failed to insert trace {trace.trace_id}")
            return False

        # 2. Insert spans (batch)
        if trace.spans:
            spans_data = [span.to_dict() for span in trace.spans]
            spans_result = client.table("spans").insert(spans_data).execute()
            if not spans_result.data:
                print(f"[tracing] Failed to insert spans for {trace.trace_id}")
                # Don't fail entirely, trace is already saved

        # 3. Insert events (batch)
        if trace.events:
            events_data = [event.to_dict() for event in trace.events]
            events_result = client.table("events").insert(events_data).execute()
            if not events_result.data:
                print(f"[tracing] Failed to insert events for {trace.trace_id}")
                # Don't fail entirely

        # 4. Update trace with final counts (in case spans/events were added after to_dict)
        client.table("traces").update({
            "span_count": len(trace.spans),
            "event_count": len(trace.events),
            "root_span_id": trace.root_span_id,
        }).eq("id", trace.id).execute()

        print(f"[tracing] Flushed trace {trace.trace_id}: {len(trace.spans)} spans, {len(trace.events)} events")
        return True

    except Exception as e:
        # Log but don't crash
        print(f"[tracing] Error flushing trace {trace.trace_id}: {e}")
        return False


async def flush_span(span: "Span", trace_id: str) -> bool:
    """
    Flush a single span immediately (for long-running operations).

    Args:
        span: The Span to flush
        trace_id: The trace DB ID

    Returns:
        True if flush succeeded
    """
    if not is_tracing_enabled():
        return True

    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            return False

        client = create_client(supabase_url, supabase_key)

        span_data = span.to_dict()
        client.table("spans").insert(span_data).execute()

        return True

    except Exception as e:
        print(f"[tracing] Error flushing span {span.span_id}: {e}")
        return False
