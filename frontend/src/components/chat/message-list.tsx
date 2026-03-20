"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./message-bubble";
import type { ChatMessage } from "@/types/session";

export function MessageList({
  messages,
  isStreaming,
}: {
  messages: ChatMessage[];
  isStreaming: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--muted-foreground)]">
        Send a message to start the conversation.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-3xl mx-auto space-y-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} className="animate-fade-in" />
        ))}
        {isStreaming && (
          <div className="flex items-center gap-2 text-[var(--muted-foreground)] text-sm">
            <span className="dot-bounce flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-current inline-block" />
              <span className="w-1.5 h-1.5 rounded-full bg-current inline-block" />
              <span className="w-1.5 h-1.5 rounded-full bg-current inline-block" />
            </span>
            <span>Agent is working...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
