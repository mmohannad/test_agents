import { NextRequest, NextResponse } from "next/server";

const CONDENSER_URL =
  process.env.CONDENSER_URL ?? "http://localhost:8012";

// Condenser typically takes 10-30 seconds for LLM analysis
const TIMEOUT_MS = 60_000; // 1 minute

/**
 * Server-side proxy for the condenser agent ACP endpoint.
 * Avoids CORS issues by making the cross-origin call from the server.
 */
export async function POST(req: NextRequest) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const body = await req.json();

    console.log("[condenser-proxy] Forwarding request to agent...");
    const startTime = Date.now();

    const res = await fetch(`${CONDENSER_URL}/api`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const elapsed = Date.now() - startTime;
    console.log(`[condenser-proxy] Agent responded in ${elapsed}ms with status ${res.status}`);

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`[condenser-proxy] Agent error: ${res.status} - ${text}`);
      return NextResponse.json(
        { error: `Condenser agent returned ${res.status}: ${text || res.statusText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    clearTimeout(timeoutId);

    if (err instanceof Error && err.name === "AbortError") {
      console.error(`[condenser-proxy] Request timed out after ${TIMEOUT_MS}ms`);
      return NextResponse.json(
        { error: `Condenser agent timed out after ${TIMEOUT_MS / 1000}s. The document analysis may be too complex.` },
        { status: 504 }
      );
    }

    const msg = err instanceof Error ? err.message : String(err);
    console.error(`[condenser-proxy] Fetch error: ${msg}`);
    return NextResponse.json(
      { error: `Failed to reach condenser agent: ${msg}` },
      { status: 502 }
    );
  }
}

// Configure Next.js to allow longer execution time for this route
export const maxDuration = 60; // 1 minute (requires Next.js 13.4.1+)
