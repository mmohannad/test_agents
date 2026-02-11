"""
Tracing library for POA agents.

Provides automatic instrumentation for capturing agent execution traces
including LLM calls, embeddings, semantic search, and tool operations.

Usage:
    from shared.tracing import Trace, current_trace, current_span

    async def handle_request():
        with Trace(agent_name="condenser", application_id=app_id) as trace:
            # All instrumented client calls are automatically traced
            result = await llm_client.chat(...)
"""

from .context import (
    current_trace,
    current_span,
    set_current_trace,
    set_current_span,
)
from .models import Trace, Span, Event
from .ids import generate_trace_id, generate_span_id, generate_event_id
from .persistence import flush_trace, is_tracing_enabled, set_tracing_enabled
from .instrumented import (
    InstrumentedLLMClient,
    InstrumentedSupabaseClient,
    traced_tool_call,
)

__all__ = [
    # Context
    "current_trace",
    "current_span",
    "set_current_trace",
    "set_current_span",
    # Models
    "Trace",
    "Span",
    "Event",
    # ID generation
    "generate_trace_id",
    "generate_span_id",
    "generate_event_id",
    # Persistence
    "flush_trace",
    "is_tracing_enabled",
    "set_tracing_enabled",
    # Instrumented clients
    "InstrumentedLLMClient",
    "InstrumentedSupabaseClient",
    "traced_tool_call",
]
