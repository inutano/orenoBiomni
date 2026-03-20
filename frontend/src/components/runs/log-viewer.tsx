"use client";

import type { Log } from "@/types/wes";

export function LogViewer({ log }: { log: Log | null }) {
  if (!log) {
    return (
      <div className="text-sm text-[var(--muted-foreground)]">
        No logs available.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {log.cmd && (
        <div>
          <h4 className="text-xs font-medium text-[var(--muted-foreground)] mb-1">
            Command
          </h4>
          <pre className="bg-[var(--muted)] rounded p-2 text-xs overflow-x-auto">
            {log.cmd.join(" ")}
          </pre>
        </div>
      )}

      {log.stdout && (
        <div>
          <h4 className="text-xs font-medium text-[var(--muted-foreground)] mb-1">
            stdout
          </h4>
          <pre className="bg-[var(--muted)] rounded p-2 text-xs overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap">
            {log.stdout}
          </pre>
        </div>
      )}

      {log.stderr && (
        <div>
          <h4 className="text-xs font-medium text-[var(--muted-foreground)] mb-1">
            stderr
          </h4>
          <pre className="bg-red-50 dark:bg-red-900/20 rounded p-2 text-xs overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap text-[var(--destructive)]">
            {log.stderr}
          </pre>
        </div>
      )}

      {log.exit_code !== null && (
        <div className="text-xs text-[var(--muted-foreground)]">
          Exit code: <span className="font-mono">{log.exit_code}</span>
        </div>
      )}
    </div>
  );
}
