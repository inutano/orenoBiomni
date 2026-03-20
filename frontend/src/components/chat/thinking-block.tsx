"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

const TRUNCATE_LIMIT = 500;

export function ThinkingBlock({ content }: { content: string }) {
  const [open, setOpen] = useState(false);
  const [showFull, setShowFull] = useState(false);
  const isLong = content.length > TRUNCATE_LIMIT;
  const displayed =
    open && isLong && !showFull
      ? content.slice(0, TRUNCATE_LIMIT) + "... (truncated)"
      : content;

  return (
    <div className="border border-[var(--border)] rounded-lg overflow-hidden text-sm">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left bg-[var(--muted)] text-[var(--muted-foreground)] hover:opacity-80"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Brain size={14} />
        <span>Thinking</span>
        {isLong && !open && (
          <span className="ml-auto text-xs opacity-60">
            {content.length.toLocaleString()} chars
          </span>
        )}
      </button>
      {open && (
        <div className="px-3 py-2 text-[var(--muted-foreground)] whitespace-pre-wrap break-all">
          {displayed}
          {isLong && (
            <button
              onClick={() => setShowFull(!showFull)}
              className="block mt-1 text-xs text-[var(--accent)] hover:underline"
            >
              {showFull ? "Show less" : "Show all"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
