"use client";

import { useEffect } from "react";
import { useChat } from "@/hooks/use-chat";
import { getSession } from "@/lib/api-client";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import type { ChatMessage } from "@/types/session";

export function ChatPanel({ sessionId }: { sessionId: string }) {
  const { messages, isStreaming, error, sendMessage, stop, loadHistory } =
    useChat(sessionId);

  useEffect(() => {
    let cancelled = false;
    getSession(sessionId).then((session) => {
      if (cancelled) return;
      const history: ChatMessage[] = session.messages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
        type: (m.message_type || (m.role === "user" ? "user" : "solution")) as ChatMessage["type"],
      }));
      loadHistory(history);
    });
    return () => {
      cancelled = true;
    };
  }, [sessionId, loadHistory]);

  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} isStreaming={isStreaming} />
      {error && (
        <div className="px-4 py-2 text-sm text-[var(--destructive)] bg-red-50 dark:bg-red-900/20">
          {error}
        </div>
      )}
      <ChatInput
        onSend={sendMessage}
        onStop={stop}
        isStreaming={isStreaming}
      />
    </div>
  );
}
