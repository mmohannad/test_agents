"""
Core tracing models: Trace, Span, Event.

These classes provide context manager support for automatic timing
and parent-child relationship tracking.
"""

import time
import uuid
import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from .context import (
    current_trace,
    current_span,
    set_current_trace,
    set_current_span,
)
from .ids import generate_trace_id, generate_span_id, generate_event_id

if TYPE_CHECKING:
    pass


def _truncate(value: Any, max_length: int = 5000) -> Any:
    """Truncate strings to avoid bloating storage."""
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + f"... [truncated, {len(value)} total chars]"
    if isinstance(value, dict):
        return {k: _truncate(v, max_length) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(v, max_length) for v in value]
    return value


@dataclass
class Event:
    """Fine-grained log entry within a span or trace."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = ""  # Human-readable ID, set after creation
    trace_db_id: Optional[str] = None  # UUID of parent trace
    span_db_id: Optional[str] = None  # UUID of parent span (optional)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    kind: str = ""  # "user_msg", "assistant_msg", "tool_call", etc.
    name: Optional[str] = None
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "trace_db_id": self.trace_db_id,
            "span_db_id": self.span_db_id,
            "timestamp": self.timestamp.isoformat(),
            "kind": self.kind,
            "name": self.name,
            "payload": _truncate(self.payload),
        }


@dataclass
class Span:
    """
    A unit of work within a trace.

    Usage:
        with trace.span("llm_call", type="llm_call") as span:
            span.set_attribute("model", "gpt-4o")
            result = await llm.chat(...)
            span.event("response", {"content": result})
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = ""  # Human-readable ID
    trace_db_id: str = ""  # UUID of parent trace
    parent_id: Optional[str] = None  # UUID of parent span
    name: str = ""
    type: str = "internal"  # llm_call, embedding, retrieval, tool_call, db_query, http, internal
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status: str = "running"  # running, success, error
    error: Optional[dict] = None
    attributes: dict = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)

    # Internal tracking
    _start_ns: int = field(default_factory=time.perf_counter_ns, repr=False)
    _event_sequence: int = field(default=0, repr=False)
    _previous_span: Optional["Span"] = field(default=None, repr=False)
    _trace_ref: Optional["Trace"] = field(default=None, repr=False)

    def __enter__(self) -> "Span":
        """Enter span context - sets this as the current span."""
        self._previous_span = current_span()
        set_current_span(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit span context - calculates duration and restores previous span."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = int((time.perf_counter_ns() - self._start_ns) / 1_000_000)

        if exc_type is not None:
            self.status = "error"
            self.error = {
                "type": exc_type.__name__,
                "message": str(exc_val),
                "traceback": traceback.format_exc()[:2000],
            }
        else:
            self.status = "success"

        # Restore previous span
        set_current_span(self._previous_span)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a single attribute."""
        self.attributes[key] = value

    def set_attributes(self, attrs: dict) -> None:
        """Set multiple attributes."""
        self.attributes.update(attrs)

    def event(self, kind: str, payload: dict = None, name: str = None) -> Event:
        """
        Record an event within this span.

        Args:
            kind: Event type (user_msg, assistant_msg, tool_call, etc.)
            payload: Event data
            name: Optional descriptive name
        """
        self._event_sequence += 1
        ev = Event(
            event_id=generate_event_id(self.span_id, self._event_sequence),
            trace_db_id=self.trace_db_id,
            span_db_id=self.id,
            kind=kind,
            name=name,
            payload=payload or {},
        )
        self.events.append(ev)

        # Also add to trace's event list
        if self._trace_ref:
            self._trace_ref.events.append(ev)

        return ev

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "span_id": self.span_id,
            "trace_db_id": self.trace_db_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "type": self.type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "attributes": _truncate(self.attributes),
        }


@dataclass
class Trace:
    """
    Root of an agent execution trace.

    Usage:
        with Trace(agent_name="condenser", application_id=app_id) as trace:
            # Instrumented clients automatically record to this trace
            result = await llm.chat(...)
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""  # Human-readable ID, generated in __post_init__
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    application_id: Optional[str] = None
    agent_name: str = ""
    agent_version: Optional[str] = None
    environment: str = "production"
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status: str = "running"  # running, success, error, timeout
    error_summary: Optional[str] = None
    root_span_id: Optional[str] = None
    span_count: int = 0
    event_count: int = 0
    metadata: dict = field(default_factory=dict)
    input_snapshot: Optional[dict] = None
    output_snapshot: Optional[dict] = None

    # Internal tracking
    spans: list[Span] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    _span_sequence: int = field(default=0, repr=False)
    _event_sequence: int = field(default=0, repr=False)
    _start_ns: int = field(default_factory=time.perf_counter_ns, repr=False)
    _root_span: Optional[Span] = field(default=None, repr=False)

    def __post_init__(self):
        """Generate trace_id if not provided."""
        if not self.trace_id:
            self.trace_id = generate_trace_id(self.agent_name)

    def __enter__(self) -> "Trace":
        """Enter trace context - sets this as the current trace."""
        set_current_trace(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit trace context - finalize and flush."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = int((time.perf_counter_ns() - self._start_ns) / 1_000_000)
        self.span_count = len(self.spans)
        self.event_count = len(self.events)

        if exc_type is not None:
            self.status = "error"
            self.error_summary = f"{exc_type.__name__}: {str(exc_val)[:200]}"
        else:
            self.status = "success"

        # Clear current trace
        set_current_trace(None)

        # Flush to database (async in background)
        self._schedule_flush()

    def span(self, name: str, type: str = "internal") -> Span:
        """
        Create a new span within this trace.

        Args:
            name: Descriptive name for the span
            type: Span type (llm_call, embedding, retrieval, tool_call, db_query, http, internal)

        Returns:
            A new Span that should be used as a context manager
        """
        self._span_sequence += 1
        parent = current_span()

        span = Span(
            span_id=generate_span_id(self.trace_id, self._span_sequence),
            trace_db_id=self.id,
            parent_id=parent.id if parent else None,
            name=name,
            type=type,
            _trace_ref=self,
        )

        # Track as root span if first span
        if self._root_span is None:
            self._root_span = span
            self.root_span_id = span.id

        self.spans.append(span)
        return span

    def event(self, kind: str, payload: dict = None, name: str = None) -> Event:
        """
        Record a trace-level event (not attached to any span).

        Args:
            kind: Event type
            payload: Event data
            name: Optional descriptive name
        """
        self._event_sequence += 1
        ev = Event(
            event_id=generate_event_id(None, self._event_sequence),
            trace_db_id=self.id,
            span_db_id=None,
            kind=kind,
            name=name,
            payload=payload or {},
        )
        self.events.append(ev)
        return ev

    def set_input(self, input_data: dict) -> None:
        """Set the input snapshot (truncated for storage)."""
        self.input_snapshot = _truncate(input_data, max_length=10000)

    def set_output(self, output_data: dict) -> None:
        """Set the output snapshot (truncated for storage)."""
        self.output_snapshot = _truncate(output_data, max_length=10000)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata field."""
        self.metadata[key] = value

    def _schedule_flush(self) -> None:
        """Schedule async flush to database."""
        from .persistence import flush_trace

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(flush_trace(self))
        except RuntimeError:
            # No running loop - we're likely in sync code
            # Create a new loop just for flushing
            try:
                asyncio.run(flush_trace(self))
            except Exception as e:
                # Log but don't crash the agent
                print(f"[tracing] Failed to flush trace: {e}")

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "application_id": self.application_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "environment": self.environment,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "error_summary": self.error_summary,
            "root_span_id": self.root_span_id,
            "span_count": self.span_count,
            "event_count": self.event_count,
            "metadata": self.metadata,
            "input_snapshot": self.input_snapshot,
            "output_snapshot": self.output_snapshot,
        }
