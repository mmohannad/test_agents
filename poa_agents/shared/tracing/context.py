"""
Thread-local context for tracing using contextvars.

Allows automatic parent-child relationship tracking for spans
without explicitly passing trace/span objects through the call stack.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import Trace, Span

# Context variables for current trace and span
_current_trace: ContextVar[Optional["Trace"]] = ContextVar(
    "current_trace", default=None
)
_current_span: ContextVar[Optional["Span"]] = ContextVar(
    "current_span", default=None
)


def current_trace() -> Optional["Trace"]:
    """Get the current active trace, or None if not in a trace context."""
    return _current_trace.get()


def current_span() -> Optional["Span"]:
    """Get the current active span, or None if not in a span context."""
    return _current_span.get()


def set_current_trace(trace: Optional["Trace"]) -> None:
    """Set the current trace (internal use)."""
    _current_trace.set(trace)


def set_current_span(span: Optional["Span"]) -> None:
    """Set the current span (internal use)."""
    _current_span.set(span)
