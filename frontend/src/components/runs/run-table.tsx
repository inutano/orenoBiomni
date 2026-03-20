"use client";

import Link from "next/link";
import { RunStateBadge } from "./run-state-badge";
import { truncateId, formatTime } from "@/lib/utils";
import type { RunSummary } from "@/types/wes";

export function RunTable({ runs }: { runs: RunSummary[] }) {
  if (runs.length === 0) {
    return (
      <div className="text-center py-12 text-[var(--muted-foreground)]">
        No runs yet. Start a chat to trigger code execution.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted-foreground)]">
            <th className="px-4 py-2 font-medium">Run ID</th>
            <th className="px-4 py-2 font-medium">State</th>
            <th className="px-4 py-2 font-medium">Started</th>
            <th className="px-4 py-2 font-medium">Ended</th>
            <th className="px-4 py-2 font-medium">Language</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.run_id}
              className="border-b border-[var(--border)] hover:bg-[var(--muted)] transition-colors"
            >
              <td className="px-4 py-2">
                <Link
                  href={`/runs/${run.run_id}`}
                  className="font-mono text-[var(--accent)] hover:underline"
                >
                  {truncateId(run.run_id)}
                </Link>
              </td>
              <td className="px-4 py-2">
                <RunStateBadge state={run.state} />
              </td>
              <td className="px-4 py-2 text-[var(--muted-foreground)]">
                {formatTime(run.start_time)}
              </td>
              <td className="px-4 py-2 text-[var(--muted-foreground)]">
                {formatTime(run.end_time)}
              </td>
              <td className="px-4 py-2 text-[var(--muted-foreground)]">
                {run.tags?.language || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
