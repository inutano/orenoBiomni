"use client";

import { ThinkingBlock } from "./thinking-block";
import { ExecuteBlock } from "./execute-block";
import { SolutionBlock } from "./solution-block";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/session";

export function MessageBubble({
  message,
  className,
}: {
  message: ChatMessage;
  className?: string;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className={cn("flex justify-end", className)}>
        <div className="max-w-[92%] md:max-w-[80%] rounded-lg px-4 py-2 bg-[var(--accent)] text-[var(--accent-foreground)]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex justify-start", className)}>
      <div className={cn("max-w-[95%] md:max-w-[85%]", message.type === "solution" && "w-full max-w-full")}>
        {message.type === "thinking" && <ThinkingBlock content={message.content} />}
        {message.type === "execute" && <ExecuteBlock content={message.content} />}
        {message.type === "solution" && <SolutionBlock content={message.content} />}
        {message.type === "error" && (
          <div className="rounded-lg px-4 py-2 bg-red-100 dark:bg-red-900/30 text-[var(--destructive)] text-sm">
            {message.content}
          </div>
        )}
      </div>
    </div>
  );
}
