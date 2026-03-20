"use client";

import { useState, useMemo } from "react";
import { useTools, useDatasets } from "@/hooks/use-tools";
import { ToolCard } from "@/components/tools/tool-card";
import { DatasetList } from "@/components/tools/dataset-list";
import { cn } from "@/lib/utils";

type Tab = "tools" | "datasets";

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("tools");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search input
  const debounceRef = useMemo(() => ({ timer: null as ReturnType<typeof setTimeout> | null }), []);

  function handleSearch(value: string) {
    setSearch(value);
    if (debounceRef.timer) clearTimeout(debounceRef.timer);
    debounceRef.timer = setTimeout(() => setDebouncedSearch(value), 300);
  }

  const { tools, isLoading: toolsLoading } = useTools(debouncedSearch || undefined);
  const { datasets, isLoading: datasetsLoading } = useDatasets(debouncedSearch || undefined);

  const isLoading = tab === "tools" ? toolsLoading : datasetsLoading;

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-bold mb-4">Tool Browser</h2>

      {/* Search bar */}
      <div className="mb-4">
        <input
          type="text"
          placeholder={`Search ${tab === "tools" ? "tools" : "datasets"}...`}
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full max-w-md px-3 py-2 text-sm border border-[var(--border)] rounded-lg bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-[var(--border)]">
        <button
          onClick={() => setTab("tools")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px",
            tab === "tools"
              ? "border-[var(--accent)] text-[var(--foreground)]"
              : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
          )}
        >
          Tools
          {!toolsLoading && (
            <span className="ml-2 text-xs text-[var(--muted-foreground)]">
              ({tools.length})
            </span>
          )}
        </button>
        <button
          onClick={() => setTab("datasets")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px",
            tab === "datasets"
              ? "border-[var(--accent)] text-[var(--foreground)]"
              : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
          )}
        >
          Datasets
          {!datasetsLoading && (
            <span className="ml-2 text-xs text-[var(--muted-foreground)]">
              ({datasets.length})
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="text-[var(--muted-foreground)]">Loading...</div>
      ) : tab === "tools" ? (
        tools.length === 0 ? (
          <div className="text-center py-12 text-[var(--muted-foreground)]">
            No tools found{debouncedSearch ? ` matching "${debouncedSearch}"` : ""}.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tools.map((tool) => (
              <ToolCard key={`${tool.domain}-${tool.name}`} tool={tool} />
            ))}
          </div>
        )
      ) : (
        <DatasetList datasets={datasets} />
      )}
    </div>
  );
}
