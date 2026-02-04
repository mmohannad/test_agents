import { NextRequest, NextResponse } from "next/server";

const CONDENSER_URL =
  process.env.CONDENSER_URL ?? "http://localhost:8012";

/**
 * Server-side proxy for the condenser agent ACP endpoint.
 * Avoids CORS issues by making the cross-origin call from the server.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const res = await fetch(`${CONDENSER_URL}/api`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json(
        { error: `Condenser agent returned ${res.status}: ${text || res.statusText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `Failed to reach condenser agent: ${msg}` },
      { status: 502 }
    );
  }
}
