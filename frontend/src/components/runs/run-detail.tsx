"use client";

import { useRun } from "@/hooks/use-run";
import { RunStateBadge } from "./run-state-badge";
import { LogViewer } from "./log-viewer";
import { truncateId, formatTime } from "@/lib/utils";
import { cancelRun } from "@/lib/api-client";
import { TERMINAL_STATES } from "@/types/wes";

export function RunDetail({ runId }: { runId: string }) {
  const { run, isLoading, refresh } = useRun(runId);

  if (isLoading) {
    return <div className="p-6 text-[var(--muted-foreground)]">Loading...</div>;
  }

  if (!run) {
    return <div className="p-6 text-[var(--destructive)]">Run not found.</div>;
  }

  const canCancel = !TERMINAL_STATES.includes(run.state);

  async function handleCancel() {
    await cancelRun(runId);
    refresh();
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-bold font-mono">{truncateId(runId, 12)}</h2>
        <RunStateBadge state={run.state} />
        {canCancel && (
          <button
            onClick={handleCancel}
            className="text-sm px-3 py-1 rounded border border-[var(--destructive)] text-[var(--destructive)] hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            Cancel
          </button>
        )}
      </div>

      <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
        <dt className="text-[var(--muted-foreground)]">Full ID</dt>
        <dd className="font-mono">{run.run_id}</dd>
        <dt className="text-[var(--muted-foreground)]">Started</dt>
        <dd>{formatTime(run.run_log?.start_time ?? null)}</dd>
        <dt className="text-[var(--muted-foreground)]">Ended</dt>
        <dd>{formatTime(run.run_log?.end_time ?? null)}</dd>
      </dl>

      <div>
        <h3 className="text-sm font-medium mb-2">Logs</h3>
        <LogViewer log={run.run_log} />
      </div>
    </div>
  );
}
