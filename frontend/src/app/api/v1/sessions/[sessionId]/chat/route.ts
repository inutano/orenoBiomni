import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

/**
 * Streaming proxy for SSE chat endpoint.
 * Next.js rewrites may buffer SSE responses, so we manually
 * proxy the request and pipe the stream through.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;
  const body = await request.text();

  const upstream = await fetch(
    `${BACKEND_URL}/api/v1/sessions/${sessionId}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
  );

  if (!upstream.ok) {
    return new Response(await upstream.text(), { status: upstream.status });
  }

  // Pipe the SSE stream through without buffering
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
