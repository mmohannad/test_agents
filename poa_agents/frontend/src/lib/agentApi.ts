// Calls go through the Next.js API route to avoid CORS issues.
// The route handler proxies to the actual agent at CONDENSER_URL (server-side).
const PROXY_URL = "/api/agent/condenser";

export interface AgentPayload {
  case_data: {
    application: Record<string, unknown>;
    parties: Record<string, unknown>[];
    capacity_proofs: Record<string, unknown>[];
  };
  document_extractions: Record<string, unknown>[];
  additional_context: Record<string, unknown>;
}

/**
 * JSON-RPC 2.0 response from the agent.
 *
 * The ACP server wraps the TextContent in a SendMessageResponse:
 *   result.content = { author, content (string), type, ... }
 *
 * So the actual markdown lives at result.content.content.
 */
export interface JSONRPCResponse {
  jsonrpc: string;
  id: string;
  result?: {
    type?: string;
    index?: number;
    parent_task_message?: unknown;
    content?: { type?: string; author?: string; content?: string };
  } | null;
  error?: { code: number; message: string } | null;
}

/**
 * Call the condenser agent via ACP JSON-RPC 2.0 endpoint (Mode B — direct input).
 *
 * The agent receives the full payload inline and skips its own Supabase fetch.
 * It runs the same LLM prompt as CLI mode and returns the legal brief.
 *
 * Protocol: POST /api with JSON-RPC 2.0 body, method "message/send".
 */
export async function runCondenserAgent(
  payload: AgentPayload
): Promise<string> {
  const now = new Date().toISOString();

  // Build the JSON-RPC 2.0 request matching ACP SendMessageParams schema
  const rpcBody = {
    jsonrpc: "2.0",
    method: "message/send",
    params: {
      agent: {
        id: "condenser-agent",
        name: "condenser-agent",
        acp_type: "sync",
        description: "Condenser agent",
        created_at: now,
        updated_at: now,
      },
      task: {
        id: `frontend-${Date.now()}`,
      },
      content: {
        type: "text",
        author: "user",
        content: JSON.stringify({
          case_data: payload.case_data,
          document_extractions: payload.document_extractions,
          additional_context: payload.additional_context,
        }),
      },
    },
    id: `req-${Date.now()}`,
  };

  const res = await fetch(PROXY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rpcBody),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(
      (data as { error?: string }).error ??
        `Condenser agent returned ${res.status}`
    );
  }

  const rpc = data as JSONRPCResponse;

  if (rpc.error) {
    throw new Error(`Agent RPC error ${rpc.error.code}: ${rpc.error.message}`);
  }

  // result is a SendMessageResponse: { content: TextContent, index, type, ... }
  // TextContent is: { author, content (string), type, format, ... }
  // So the actual markdown lives at result.content.content
  const textContent = rpc.result?.content;
  const markdown = textContent?.content;
  if (!markdown) {
    throw new Error("Agent returned empty response");
  }

  return markdown;
}

/**
 * Parse the condenser result content.
 *
 * The agent returns markdown with an embedded JSON block inside a <details> tag:
 *
 *   <details>
 *   <summary>Raw JSON for Legal Search Agent</summary>
 *
 *   ```json
 *   { ... }
 *   ```
 *   </details>
 *
 * This function extracts and parses that JSON. If the content is already valid
 * JSON (no markdown wrapper), it parses directly. Falls back to raw string.
 */
export function parseCondenserContent(
  raw: string
): Record<string, unknown> | string {
  // 1. Try direct JSON parse (agent may return pure JSON string)
  try {
    const direct = JSON.parse(raw);
    if (typeof direct === "object" && direct !== null) {
      return direct as Record<string, unknown>;
    }
  } catch {
    // Not pure JSON — try extraction
  }

  // 2. Extract from ```json ... ``` fenced code block (inside <details>)
  const fencedMatch = raw.match(/```json\s*\n([\s\S]*?)\n\s*```/);
  if (fencedMatch) {
    try {
      const parsed = JSON.parse(fencedMatch[1]);
      if (typeof parsed === "object" && parsed !== null) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      // Malformed JSON inside fence — fall through
    }
  }

  // 3. Fallback: return raw markdown string
  return raw;
}
