"use client";

import { useCallback, useRef, useState } from "react";
import { streamChat } from "@/lib/sse-client";
import type { ChatMessage } from "@/types/session";

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback((history: ChatMessage[]) => {
    setMessages(history);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!sessionId || isStreaming) return;

      setError(null);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text, type: "user" },
      ]);
      setIsStreaming(true);

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        for await (const event of streamChat(sessionId, text, abort.signal)) {
          if (event.event === "done") break;

          const content =
            (event.data as { content?: string }).content ||
            (event.data as { error?: string }).error ||
            "";

          if (content) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content, type: event.event },
            ]);
          }
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setError((e as Error).message);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [sessionId, isStreaming],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, isStreaming, error, sendMessage, stop, loadHistory };
}
