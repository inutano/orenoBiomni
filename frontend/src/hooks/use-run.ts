"use client";

import { useCallback, useEffect, useState } from "react";
import { getRun } from "@/lib/api-client";
import type { RunLog } from "@/types/wes";
import { TERMINAL_STATES } from "@/types/wes";

export function useRun(runId: string, pollMs = 3000) {
  const [run, setRun] = useState<RunLog | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setRun(await getRun(runId));
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    refresh();

    const id = setInterval(() => {
      if (document.hidden) return;
      if (run && TERMINAL_STATES.includes(run.state)) return;
      refresh();
    }, pollMs);

    return () => clearInterval(id);
  }, [refresh, pollMs, run]);

  return { run, isLoading, refresh };
}
