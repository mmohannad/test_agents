// Calls go through Next.js API routes to avoid CORS issues.
// The route handlers proxy to the actual agents (server-side).
const CONDENSER_PROXY = "/api/agent/condenser";
const LEGAL_SEARCH_PROXY = "/api/agent/legal-search";

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
 * JSON-RPC 2.0 response from an agent.
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
 * Build a JSON-RPC 2.0 request body for an ACP message/send call.
 */
function buildRpcBody(agentId: string, contentPayload: string) {
  const now = new Date().toISOString();
  return {
    jsonrpc: "2.0",
    method: "message/send",
    params: {
      agent: {
        id: agentId,
        name: agentId,
        acp_type: "sync",
        description: `${agentId} agent`,
        created_at: now,
        updated_at: now,
      },
      task: {
        id: `frontend-${Date.now()}`,
      },
      content: {
        type: "text",
        author: "user",
        content: contentPayload,
      },
    },
    id: `req-${Date.now()}`,
  };
}

/**
 * Send a JSON-RPC 2.0 request to an agent proxy and extract the text content.
 */
async function callAgent(proxyUrl: string, rpcBody: unknown): Promise<string> {
  const res = await fetch(proxyUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rpcBody),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(
      (data as { error?: string }).error ??
        `Agent returned ${res.status}`
    );
  }

  const rpc = data as JSONRPCResponse;

  if (rpc.error) {
    throw new Error(`Agent RPC error ${rpc.error.code}: ${rpc.error.message}`);
  }

  // result is a SendMessageResponse: { content: TextContent, index, type, ... }
  // TextContent is: { author, content (string), type, format, ... }
  // So the actual markdown lives at result.content.content
  const markdown = rpc.result?.content?.content;
  if (!markdown) {
    throw new Error("Agent returned empty response");
  }

  return markdown;
}

/**
 * Call the condenser agent via ACP JSON-RPC 2.0 endpoint (Mode B -- direct input).
 *
 * The agent receives the full payload inline and skips its own Supabase fetch.
 * It runs the same LLM prompt as CLI mode and returns the legal brief.
 */
export async function runCondenserAgent(
  payload: AgentPayload,
  locale: string = "ar"
): Promise<string> {
  const rpcBody = buildRpcBody(
    "condenser-agent",
    JSON.stringify({
      case_data: payload.case_data,
      document_extractions: payload.document_extractions,
      additional_context: payload.additional_context,
      locale,
    })
  );

  return callAgent(CONDENSER_PROXY, rpcBody);
}

/**
 * Call the legal search agent via ACP JSON-RPC 2.0 endpoint (Mode B -- direct input).
 *
 * The agent receives the legal brief inline and skips its own Supabase fetch.
 * It runs the same decompose -> retrieve -> synthesize pipeline as CLI mode.
 */
export async function runLegalSearchAgent(
  legalBrief: Record<string, unknown>,
  locale: string = "ar"
): Promise<string> {
  const rpcBody = buildRpcBody(
    "legal-search-agent",
    JSON.stringify({ legal_brief: legalBrief, locale })
  );

  return callAgent(LEGAL_SEARCH_PROXY, rpcBody);
}

/**
 * Parse agent result content.
 *
 * Both agents return markdown with an embedded JSON block inside a <details> tag:
 *
 *   <details>
 *   <summary>Raw JSON ...</summary>
 *
 *   ```json
 *   { ... }
 *   ```
 *   </details>
 *
 * This function extracts and parses that JSON. If the content is already valid
 * JSON (no markdown wrapper), it parses directly. Falls back to raw string.
 */
export function parseAgentContent(
  raw: string
): Record<string, unknown> | string {
  // 1. Try direct JSON parse (agent may return pure JSON string)
  try {
    const direct = JSON.parse(raw);
    if (typeof direct === "object" && direct !== null) {
      return direct as Record<string, unknown>;
    }
  } catch {
    // Not pure JSON -- try extraction
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
      // Malformed JSON inside fence -- fall through
    }
  }

  // 3. Fallback: return raw markdown string
  return raw;
}
