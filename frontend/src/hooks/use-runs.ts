"use client";

import { useCallback, useEffect, useState } from "react";
import { listRuns } from "@/lib/api-client";
import type { RunSummary } from "@/types/wes";
import { TERMINAL_STATES } from "@/types/wes";

export function useRuns(sessionId?: string, pollMs = 5000) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await listRuns(sessionId);
      setRuns(res.runs);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    refresh();

    const id = setInterval(() => {
      if (document.hidden) return;
      // Stop polling if all runs are terminal
      const hasActive = runs.some(
        (r) => !TERMINAL_STATES.includes(r.state),
      );
      if (hasActive || runs.length === 0) refresh();
    }, pollMs);

    return () => clearInterval(id);
  }, [refresh, pollMs, runs]);

  return { runs, isLoading, refresh };
}
