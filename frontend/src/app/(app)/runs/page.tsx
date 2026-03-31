"use client";

import { useRuns } from "@/hooks/use-runs";
import { RunTable } from "@/components/runs/run-table";

export default function RunsPage() {
  const { runs, isLoading } = useRuns();

  return (
    <div className="p-4 md:p-6">
      <h2 className="text-lg font-bold mb-4">Workflow Runs</h2>
      {isLoading ? (
        <div className="text-[var(--muted-foreground)]">Loading...</div>
      ) : (
        <RunTable runs={runs} />
      )}
    </div>
  );
}
