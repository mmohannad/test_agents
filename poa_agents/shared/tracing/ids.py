"""
ID generation for traces, spans, and events.

Format:
- Trace ID: tr_{YYYYMMDD}_{agent}_{random8}
- Span ID: sp_{trace_short}_{sequence}_{random4}
- Event ID: ev_{span_short}_{sequence}
"""

import time
import uuid
from typing import Optional


def generate_trace_id(agent_name: str) -> str:
    """
    Generate a human-readable trace ID.

    Format: tr_{YYYYMMDD}_{agent}_{random8}
    Example: tr_20260211_condenser_a1b2c3d4
    """
    date_str = time.strftime("%Y%m%d")
    random_suffix = uuid.uuid4().hex[:8]
    # Sanitize agent name (remove spaces, lowercase)
    safe_agent = agent_name.lower().replace(" ", "_").replace("-", "_")[:20]
    return f"tr_{date_str}_{safe_agent}_{random_suffix}"


def generate_span_id(trace_id: str, sequence: int) -> str:
    """
    Generate a human-readable span ID.

    Format: sp_{trace_short}_{sequence}_{random4}
    Example: sp_a1b2c3d4_001_x9y8
    """
    # Extract the random part from trace_id (last 8 chars)
    trace_short = trace_id.split("_")[-1] if "_" in trace_id else trace_id[:8]
    random_suffix = uuid.uuid4().hex[:4]
    return f"sp_{trace_short}_{sequence:03d}_{random_suffix}"


def generate_event_id(span_id: Optional[str], sequence: int) -> str:
    """
    Generate a human-readable event ID.

    Format: ev_{span_short}_{sequence}
    Example: ev_001x9y8_001
    """
    if span_id:
        # Extract sequence and random from span_id
        parts = span_id.split("_")
        if len(parts) >= 3:
            span_short = f"{parts[-2]}{parts[-1]}"  # e.g., "001x9y8"
        else:
            span_short = span_id[-8:]
    else:
        span_short = "trace"
    return f"ev_{span_short}_{sequence:03d}"
