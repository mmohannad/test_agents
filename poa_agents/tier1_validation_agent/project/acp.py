"""
ACP Server for Tier 1 Validation Agent.
Handles AgentEx protocol for temporal workflows.
"""

import os
import sys

# === DEBUG SETUP (AgentEx CLI Debug Support) ===
if os.getenv("AGENTEX_DEBUG_ENABLED") == "true":
    try:
        import debugpy

        debug_port = int(os.getenv("AGENTEX_DEBUG_PORT", "5679"))
        debug_type = os.getenv("AGENTEX_DEBUG_TYPE", "acp")
        wait_for_attach = (
            os.getenv("AGENTEX_DEBUG_WAIT_FOR_ATTACH", "false").lower() == "true"
        )

        debugpy.configure(subProcess=False)
        debugpy.listen(debug_port)

        print(f"🐛 [{debug_type.upper()}] Debug server listening on port {debug_port}")

        if wait_for_attach:
            print(f"⏳ [{debug_type.upper()}] Waiting for debugger to attach...")
            debugpy.wait_for_client()
            print(f"✅ [{debug_type.upper()}] Debugger attached!")
        else:
            print(f"📡 [{debug_type.upper()}] Ready for debugger attachment")

    except ImportError:
        print("❌ debugpy not available. Install with: pip install debugpy")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Debug setup failed: {e}")
        sys.exit(1)
# === END DEBUG SETUP ===

from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.fastacp import TemporalACPConfig


# Create the ACP server for temporal workflow
acp = FastACP.create(
    acp_type="agentic",
    config=TemporalACPConfig(
        type="temporal",
        temporal_address=os.getenv("TEMPORAL_ADDRESS", "localhost:7233"),
    ),
)
