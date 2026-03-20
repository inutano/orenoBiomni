"use client";

import { cn } from "@/lib/utils";
import type { ToolModule } from "@/types/tools";

function formatDomain(domain: string): string {
  return domain
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ToolCard({
  tool,
  onClick,
}: {
  tool: ToolModule;
  onClick?: () => void;
}) {
  return (
    <div
      className={cn(
        "border border-[var(--border)] rounded-lg p-4 hover:bg-[var(--muted)] transition-colors",
        onClick && "cursor-pointer",
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-medium text-sm">{formatDomain(tool.name)}</h3>
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 shrink-0">
          {tool.domain}
        </span>
      </div>
      <p className="text-xs text-[var(--muted-foreground)] line-clamp-2 mb-3">
        {tool.description || "No description available"}
      </p>
      <div className="text-xs text-[var(--muted-foreground)]">
        {tool.function_count} {tool.function_count === 1 ? "function" : "functions"}
      </div>
    </div>
  );
}
