import { NextRequest, NextResponse } from "next/server";

const LEGAL_SEARCH_URL =
  process.env.LEGAL_SEARCH_URL ?? "http://localhost:8013";

// Legal search can take 60-120+ seconds due to multiple LLM calls
// (decomposition, HyDE hypotheticals, retrieval iterations, synthesis)
const TIMEOUT_MS = 180_000; // 3 minutes

/**
 * Server-side proxy for the legal search agent ACP endpoint.
 * Avoids CORS issues by making the cross-origin call from the server.
 */
export async function POST(req: NextRequest) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const body = await req.json();

    console.log("[legal-search-proxy] Forwarding request to agent...");
    const startTime = Date.now();

    const res = await fetch(`${LEGAL_SEARCH_URL}/api`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const elapsed = Date.now() - startTime;
    console.log(`[legal-search-proxy] Agent responded in ${elapsed}ms with status ${res.status}`);

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`[legal-search-proxy] Agent error: ${res.status} - ${text}`);
      return NextResponse.json(
        { error: `Legal search agent returned ${res.status}: ${text || res.statusText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    clearTimeout(timeoutId);

    if (err instanceof Error && err.name === "AbortError") {
      console.error(`[legal-search-proxy] Request timed out after ${TIMEOUT_MS}ms`);
      return NextResponse.json(
        { error: `Legal search agent timed out after ${TIMEOUT_MS / 1000}s. The analysis may be too complex or the agent is overloaded.` },
        { status: 504 }
      );
    }

    const msg = err instanceof Error ? err.message : String(err);
    console.error(`[legal-search-proxy] Fetch error: ${msg}`);
    return NextResponse.json(
      { error: `Failed to reach legal search agent: ${msg}` },
      { status: 502 }
    );
  }
}

// Configure Next.js to allow longer execution time for this route
export const maxDuration = 180; // 3 minutes (requires Next.js 13.4.1+)
