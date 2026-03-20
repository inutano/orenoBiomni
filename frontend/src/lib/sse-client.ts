import type { SSEEvent, SSEEventType } from "@/types/session";

/**
 * Stream SSE events from a POST-based chat endpoint.
 * EventSource only supports GET, so we use fetch + ReadableStream.
 */
export async function* streamChat(
  sessionId: string,
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`/api/v1/sessions/${sessionId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });

  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Normalize \r\n to \n (sse-starlette sends \r\n line endings)
    buffer = buffer.replace(/\r\n/g, "\n");

    // SSE frames are delimited by double newlines
    const frames = buffer.split("\n\n");
    buffer = frames.pop()!; // keep incomplete frame in buffer

    for (const frame of frames) {
      const event = parseSSEFrame(frame);
      if (event) yield event;
    }
  }

  // Process any remaining buffer
  if (buffer.trim()) {
    const event = parseSSEFrame(buffer);
    if (event) yield event;
  }
}

function parseSSEFrame(frame: string): SSEEvent | null {
  let eventType: SSEEventType = "thinking";
  let dataStr = "";

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim() as SSEEventType;
    } else if (line.startsWith("data:")) {
      dataStr = line.slice(5).trim();
    } else if (line.startsWith(": ")) {
      // Comment line (e.g., ping), skip
      continue;
    }
  }

  if (!dataStr) return null;

  try {
    return { event: eventType, data: JSON.parse(dataStr) };
  } catch {
    return null;
  }
}
